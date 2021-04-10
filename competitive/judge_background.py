# import dramatiq
from AOJ.celery import app
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from control.models import Setting

from .forms import SubmitAnswer
import requests
from .models import Submit, Contest
from judgeserver.models import JudgeServer
from problem.views import update_statistics
from competitive.models import RankcacheJury, RankcachePublic, ScorecacheJury, ScorecachePublic

def time_gap(submit_time, contest_start_time):
    td = submit_time - contest_start_time
    time_taken = td.seconds // 60 + td.days * 1400
    return time_taken


def setting_values():
    try:
        punish_value = Setting.objects.get(name="punish time").value
    except Setting.DoesNotExist:
        punish_value = 20

    try:
        rating_correct_value = Setting.objects.get(
            name="rating correct value").value
    except Setting.DoesNotExist:
        rating_correct_value = 20

    try:
        rating_punish_value = Setting.objects.get(
            name="rating punish value").value
    except Setting.DoesNotExist:
        rating_punish_value = 1

    return (punish_value, rating_correct_value, rating_punish_value)

def rank_update(submit):
   if not submit.user.role.short_name == "contestant":
      return
   if not submit.result:
      return
   if submit.submit_time < submit.contest.start_time:
      return
   if submit.submit_time >= submit.contest.end_time:
      return
   pro = submit.problem
   contest = submit.contest
   this_problem_prevous_correct_submit = Submit.objects.filter(
      contest=contest, problem=pro, result='Correct', submit_time__lte=submit.submit_time, user=submit.user).exclude(pk=submit.pk)
   if this_problem_prevous_correct_submit:
      return

   try:
      rank_cache = RankcacheJury.objects.get(
         user=submit.user, contest=contest)
   except RankcacheJury.DoesNotExist:
      rank_cache = RankcacheJury(user=submit.user, contest=contest)
      rank_cache.save()

   try:
      rank_cache_public = RankcachePublic.objects.get(
         user=submit.user, contest=contest)
   except RankcachePublic.DoesNotExist:
      rank_cache_public = RankcachePublic(user=submit.user, contest=contest)
      rank_cache_public.save()

   try:
      score_cache = ScorecacheJury.objects.get(
         rank_cache=rank_cache, problem=pro)
   except ScorecacheJury.DoesNotExist:
      score_cache = ScorecacheJury(rank_cache=rank_cache, problem=pro)
      score_cache.save()

   try:
      score_cache_public = ScorecachePublic.objects.get(
         rank_cache=rank_cache_public, problem=pro)
   except ScorecachePublic.DoesNotExist:
      score_cache_public = ScorecachePublic(
         rank_cache=rank_cache_public, problem=pro)
      score_cache_public.save()

   if score_cache.is_correct:
      return
   score_cache.submission += 1
   if submit.result == "Correct":
      score_cache.is_correct = True
      score_cache.correct_submit_time = submit.submit_time
   elif submit.result == "Compiler Error":
      pass
   else:
      score_cache.punish += 1
   score_cache.save()

   if submit.result == "Correct":
      punish_value, rating_correct_value, rating_punish_value = setting_values()
      rank_cache.point = (float(rank_cache.point) + float(pro.point))
      rank_cache.punish_time += punish_value * score_cache.punish + \
         time_gap(score_cache.correct_submit_time, contest.start_time)
      rank_cache.save()
      if contest.has_value:  # rating update
         user = submit.user
         user.rating += (rating_correct_value -
                           rating_punish_value * score_cache.punish)
         user.save()

   if contest.frozen_time and contest.unfrozen_time and contest.frozen_time <= submit.submit_time and submit.submit_time < contest.unfrozen_time:
      score_cache_public.submission += 1
      score_cache_public.pending += 1
      score_cache_public.save()
   else:
      rank_cache_public.point = rank_cache.point
      rank_cache_public.punish_time = rank_cache.punish_time
      rank_cache_public.save()

      score_cache_public.submission = score_cache.submission
      score_cache_public.punish = score_cache.punish
      score_cache_public.correct_submit_time = score_cache.correct_submit_time
      score_cache_public.is_correct = score_cache.is_correct
      score_cache_public.save()

   score_cache_public.judging -= 1
   score_cache_public.save()
   score_cache.judging -= 1
   score_cache.save()

   this_contest = submit.contest
   this_contest.last_update = timezone.now()
   this_contest.save()   

class ChooseJudgeServer:
   def __init__(self):
      self.server = None

   def __enter__(self) -> [JudgeServer, None]:
      with transaction.atomic():
         servers = JudgeServer.objects.select_for_update().filter(is_enabled=True).order_by("load")
         servers = [s for s in servers if s.status == "normal"]
         for server in servers:
            # if server.load <= server.server_cpu_number * 2:
            server.load = F("load") + 1
            # server.load += 1
            # server.save()
            server.save(update_fields=["load"])
            self.server = server
            return server
         
      return None

   def __exit__(self, exc_type, exc_val, exc_tb):
      if self.server:
         JudgeServer.objects.filter(id=self.server.id).update(load=F("load") -  1)


# @dramatiq.actor
@app.task
def judge_background(submission_id):
   submission = Submit.objects.get(id=submission_id)
   print(submission.language)
   # post = form.save(commit=False)
  
   with ChooseJudgeServer() as server:
      url = server.address + "/judge"
      try:
         with open(submission.submit_file.path, 'r') as f:
            content = f.read()
         # kwargs = {"headers": {"X-Judge-Server-Token": 'amir'}}
         kwargs = {}
         temp_data= {
            # "headers": {"X-Judge-Server-Token": 'amir'},
            "src_code": content,
            "testcase_id": str(submission.problem.id),
            # "max_cpu_time": int(10000 * submission.problem.time_limit),
            "max_real_time": int(1000000 * submission.problem.time_limit),
            "max_memory": submission.problem.memory_limit,
            "language": submission.language.name,
            # "language": 'cpp'
         }
         # print(temp_data)
         kwargs['json'] = temp_data
         
         judge_server_result = requests.get(url, **kwargs).json()
         
         # print('hello')
         # print(type(judge_server_result))
         # print(judge_server_result)
         # print(judge_server_result['success'])
         # print()
         if judge_server_result['success']:
            for item in judge_server_result['data']:
               if item['result'] == 0:
                  total_result = 'Correct'
                  continue
               elif item['result'] == 2 or item['result'] == 3:
                  total_result = 'Time Limit Exceeded'
                  break
               elif item['result'] == 4:
                  total_result = 'Memory Limit Exceeded'
                  break
               elif item['result'] == 5:
                  total_result = 'Runtime Error'
                  break
               elif item['result'] == -1:
                  total_result = 'Wrong Answer'
                  break
            submission.result = total_result
         elif judge_server_result['error'] == 'CompileError':
            submission.result = "Compile Error"
            
      except Exception as e:
         # result = judge(file_name=post.submit_file.path,
         #             problem=post.problem, language=post.language, submit=post)
         # post.result = result
         # print(e)
         pass


   submission.save()
   rank_update(submission)
   update_statistics(submission)
