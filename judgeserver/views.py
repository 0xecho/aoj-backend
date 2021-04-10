from django.shortcuts import render, redirect, HttpResponse
import requests
from django.contrib import messages
from authentication.decorators import admin_auth
from django.contrib.auth.decorators import login_required
from problem.models import Problem, TestCase
import requests
from .models import JudgeServer
from .forms import AddJudgeserver
from zipfile import ZipFile
import os
from os.path import basename
import hashlib
import json

# Create your views here.

@login_required
@admin_auth
def judgeserver_list(request):
   judgeservers = JudgeServer.objects.all()
   for judgeserver in judgeservers:
      try:
         info = requests.get(judgeserver.address + '/info').json()
         judgeserver.server_name = info['hostname']
         judgeserver.server_cpu_number = info['cpu_core']
         judgeserver.server_cpu_usage = info['cpu']
         judgeserver.status = 'normal'
         judgeserver.command_runner_version = info['CommandRunner_version']
         judgeserver.save()
         print()
         print()
         print(info)
      except Exception as e:
         judgeserver.server_name = 'unknown'
         judgeserver.server_cpu_number = None
         judgeserver.server_cpu_usage = None
         judgeserver.command_runner_version = 'unknown'
         judgeserver.status = 'abnormal'
         judgeserver.save()

   return render(request, 'judgeserver_list.html', {'judgeservers': judgeservers})


# @login_required
# @admin_auth
def add_judgeserver(request):
    if request.method == "POST":
        form = AddJudgeserver(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.save()
            return redirect('judgeserver_list')
    else:
        form = AddJudgeserver()
    return render(request, 'add_judgeserver.html', {'form': form, 'cont': 'hover'})

@admin_auth
def edit_judgeserver(request, judgeserver_id):
   judgeserver = JudgeServer.objects.get(pk=judgeserver_id)
   if request.method == "POST":
      form = AddJudgeserver(request.POST, instance=judgeserver)
    
      if form.is_valid():
         post = form.save(commit=False)
         post.save()
         return redirect('judgeserver_list')
   else:
      form = AddJudgeserver(instance=judgeserver)
   return render(request, 'edit_judgeserver.html', {'form': form, 'judgeserver_id': judgeserver.id, 'cont': 'hover'})


# @login_required
# @admin_auth_and_contest_exist
def delete_judgeserver(request, judgeserver_id):
    judgeserver = JudgeServer.objects.get(pk=judgeserver_id)
    return render(request, 'delete_judgeserver.html', {'judgeserver': judgeserver, 'cont': 'hover'})


# @login_required
# @admin_auth_and_contest_exist
def delete_judgeserver_done(request, judgeserver_id):
    judgeserver = JudgeServer.objects.get(id=judgeserver_id)
    judgeserver.delete()
    messages.success(request, "The judgeserver " +
                     judgeserver.address + " was deleted successfully.")
    return redirect('judgeserver_list')


def _get_sha256(output_file):
		with open(output_file, 'rb') as f:
			content = f.read()
		return hashlib.sha256(content.rstrip()).hexdigest()


def testcase_name(path):
   index = path.rfind('/')
   return path[index + 1:]


def testcase_info(problem, path):
   testcase = TestCase.objects.filter(problem=problem)
   count = len(testcase)
   info = ""
   info += '{"number_of_testcases": %d, "testcases": {' %count
   info_list = []
   for test in testcase:
      temp_info = ""
      output_file = testcase_name(test.output.path)
      input_file = testcase_name(test.input.path)
      sha256 = _get_sha256(test.output.path)
      temp_info += '"%s": { "input_name": "%s", "output_name": "%s",' % (test.name, input_file, output_file)
      temp_info += '"sha256_output": "%s"}' % sha256
      info_list.append(temp_info)
   info += ",".join(info_list)
   info += "}}"

   info_file = open(path, "w")
   info_file.write(info)
   info_file.close()
   return info


# @admin_auth
def dump_judgeserver(request, judgeserver_id):
   judgeserver = JudgeServer.objects.get(pk=judgeserver_id)
   all_problem = [pro for pro in Problem.objects.all()]
   server_problem = [pro for pro in judgeserver.problem.all()]
   dump_problem = [pro for pro in all_problem if not pro in server_problem]
   
   BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

   # with ZipFile('testcases.zip', 'w') as zipObj2:
      # Add multiple files to the zip
      # zipObj2.write('sample_file.csv')
   for problem in dump_problem:
      pro_path = problem.pdf.path
      index = pro_path.rfind('/')
      pro_path = pro_path[:index]
      dirName = pro_path + "/testcase"

      filePath = os.path.join(dirName, "info")
      testcase_info(problem, filePath)
      path = os.path.join(BASE_DIR, '%d.zip' %problem.id)
      with ZipFile(path , 'w') as zipObj:
         for folderName, subfolders, filenames in os.walk(dirName):
            for filename in filenames:

               filePath = os.path.join(folderName, filename)
               zipObj.write(filePath,  basename(filePath))

      requests.post(judgeserver.address + "/upload_testcase",  files={'file': open(path, "rb")}, data={'testcase_id': str(problem.id)})
      judgeserver.problem.add(problem)
      judgeserver.save()
      os.remove(path)
   return redirect('judgeserver_list')
  
