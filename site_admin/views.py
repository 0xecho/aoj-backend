from problem.models import Problem
from django.http import JsonResponse
from competitive.models import Submit
from django.contrib.auth.decorators import login_required
from authentication.decorators import site_auth, site_auth_and_user_exist, site_auth_and_contest_exist,\
    site_auth_and_submit_exist
from authentication.models import User, Role
from django.shortcuts import render, render_to_response, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.db import IntegrityError
from authentication.validators import email_validate
import csv
from authentication.forms import PublicUserRegistrationForm, EditMyProfile,\
    CSVUserUpload, ChangePassword
from .forms import AddUser, EditUserProfile
from contest.models import Contest
from contest.views import update_rank_score, refresh_contest_session_admin
from contest.forms import EditContest
from competitive.views import update_score_and_rank, judge
# Create your views here


@login_required
@site_auth
def site_view_user(request):
    refresh_contest_session_admin(request)  # refersh the contest session
    contestant_user = User.objects.filter(role__short_name="contestant", campus=request.user.campus).order_by('username')
    jury_user = User.objects.filter(
        role__short_name="jury", campus=request.user.campus).order_by('username')
    site_admin_user = User.objects.filter(
        role__short_name="site", campus=request.user.campus).order_by('username')
    public_user = User.objects.filter(
        role__short_name="public", campus=request.user.campus).order_by('username')

    context = {
        'contestant_user': contestant_user,
        'jury_user': jury_user,
        'site_admin_user': site_admin_user,
        'public_user': public_user,
        'user': 'hover'
    }
    return render(request, 'site_user_list.html', context)


@login_required
@site_auth_and_user_exist
def delete_user(request, user_id):
    user = User.objects.get(pk=user_id)
    return render(request, 'site_delete_user.html', {'this_user': user, 'user': 'hover'})


@login_required
@site_auth_and_user_exist
def delete_user_done(request, user_id):
    user = User.objects.get(pk=user_id)
    # user_participated_contest = Contest.objects.filter(user=user)
    # for contest in user_participated_contest:
    #     contest.last_update = timezone.now()
    #     contest.save()
    user.delete()
    messages.success(request, "user " + user.name +
                     " was deleted successfully.")
    return redirect('site_view_user')


@login_required
@site_auth_and_user_exist
def edit_user(request, user_id):
    refresh_contest_session_admin(request)  # refersh the contest session
    user = User.objects.get(pk=user_id)
    if request.method == "POST":
        form = EditUserProfile(request.POST, instance=user)
        if form.is_valid():
            post = form.save(commit=False)
            post.save()
            messages.success(request, "The user " +
                             user.username+" was update successfully.")
            return redirect('site_view_user')
    else:
        form = EditUserProfile(instance=user)

    return render(request, 'site_edit_user.html', {'form': form, 'user_id': user.id, 'user': 'hover'})


@login_required
@site_auth
def user_register(request):
    refresh_contest_session_admin(request)  # refersh the contest session
    if request.method == "POST":
        form = AddUser(request.POST)
        if form.is_valid():
            chars = 'abcdefghijklmnopqrstuvwxyz0123456789@#$%&*'
            secret_key = get_random_string(8, chars)
            post = form.save(commit=False)
            post.campus = request.user.campus
            post.role = Role.objects.get(short_name='contestant')
            post.set_password(secret_key)
            post.save()
            messages.success(request, "user "+post.name +
                             " was added successfully.")
            return redirect('site_user_register')
    else:
        form = AddUser()
    form1 = CSVUserUpload()
    return render(request, 'site_user_register.html', {'form': form, 'form1': form1, 'user': 'hover'})


def validate_data(request, username, name, email, line_number):
    if not username:
        messages.error(request, "invalid username in line " + str(line_number))
        return 0
    else:
        try:
            User.objects.get(username=username)
            messages.error(request, "username " +
                           username + " was already exists.")
            return 0
        except User.DoesNotExist:
            pass

    if not name:
        messages.error(request, "invalid name for user " + username)
        return 0

    if not email_validate(email):
        messages.error(request, "invalid email for user " + username)
        return 0
    try:
        User.objects.get(email=email)
        messages.error(request, "email " +
                        email + " was already exists.")
        return 0
    except User.DoesNotExist:
        pass

    return 1


def register_csv(request, csv_file):
    if not (csv_file.content_type == 'text/csv' or csv_file.content_type == 'application/vnd.ms-excel'):
        messages.error(request, "The file is not csv format.")
        return redirect('site_user_register_csv')
    else:
        decoded_file = csv_file.read().decode('utf-7').splitlines()
        reader = csv.DictReader(decoded_file)
        line_number = 0
        for row in reader:
            # basic info
            try:
                username = row['username'].strip()
                name = row['name'].strip()
                email = row['email'].strip()
            except KeyError:
                messages.error(request, "invalid column header in csv file.Column headers must be contain username,"
                               " name, email.")
                return redirect('site_user_register_csv')

            # validate data
            val = validate_data(request, username, name, email, line_number)
            campus = request.user.campus
            role = Role.objects.get(short_name='contestant')
            if val == 0:
                continue

            try:
                chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
                if 'password' in row:
                    secret_key = row['password']
                else:
                    secret_key = get_random_string(8, chars)
                obj = User.objects.get_or_create(
                    username=username,
                    name=name,
                    email=email,
                    campus=campus,
                    role=role,
                )
                obj.set_password(secret_key)
                obj.save()

            except IntegrityError:
                messages.error(
                    request, "invalid information for user " + username)
            line_number += 1
    if not line_number:
        messages.error(request, " no user register.")
    else:
        messages.success(request, str(line_number) +
                         " user register successfully.")
    return redirect('site_user_register_csv')


@login_required
@site_auth
def user_register_csv(request):
    if request.method == "POST":
        form1 = CSVUserUpload(request.POST, request.FILES)
        if form1.is_valid():
            file = request.FILES.get('file')
            register_csv(request, file)
            return redirect('site_user_register')
    else:
        form1 = CSVUserUpload()
    form = AddUser()
    return render(request, 'site_user_register.html', {'form': form, 'form1': form1, 'user': 'hover'})


def generate_users_password_csv(request, total_users):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="User Password Generate.csv"'
    writer = csv.writer(response)
    writer.writerow(['#', 'Username', 'Name', 'Email', 'Role', 'Password'])
    for user in total_users:
        writer.writerow(user)
    return response


@login_required
@site_auth
def generate_user_password(request, role_type):
    role = Role.objects.get(short_name=role_type)
    return render(request, 'site_generate_password.html', {'role': role})


@login_required
@site_auth
def generate_password_done(request, role_id):
    role = Role.objects.get(pk=role_id)
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
    total_users = []
    count = 1
    all_users = User.objects.filter(role=role, campus=request.user.campus)
    for user in all_users:
        secret_key = get_random_string(6, chars)
        user.set_password(secret_key)
        user.save()
        total_users.append((count, user.username, user.name, user.email,
                            user.role.role, secret_key))
        count += 1
    excel = generate_users_password_csv(request, total_users)
    return excel

    return redirect('site_view_user')


@login_required
@site_auth
def site_view_problem(request):
    refresh_contest_session_admin(request)  # refersh the contest session
    total_problems = Problem.objects.all().order_by('title')
    return render(request, 'site_problem_list.html', {'problem': total_problems, 'pro': 'hover'})



@login_required
@site_auth
def site_contest_list(request):
    refresh_contest_session_admin(request)  # refersh the contest session
    total_contest = Contest.objects.all().order_by('start_time').reverse()
    now = timezone.now()
    for contest in total_contest:
        if contest.enable == False:
            contest.status = "disable"
        elif now < contest.active_time:
            contest.status = "not active"
        elif now < contest.start_time:
            contest.status = "active"
        elif contest.start_time <= now and now < contest.end_time:
            contest.status = "on going"
        elif contest.end_time <= now and now < contest.deactivate_time:
            contest.status = "end"
        else:
            contest.status = "deactivate"  
    return render(request, 'site_contest_list.html', {'contest': total_contest, 'cont': 'hover'})


@login_required
@site_auth
def site_contest_detail(request, contest_id):
    refresh_contest_session_admin(request)  # refersh the contest session
    try:
        contest = Contest.objects.get(pk=contest_id)
    except Contest.DoesNotExist:
        return redirect('homepage')

    if contest.created_by == request.user.campus:

        # refresh_contest_session_admin(request)  # refersh the contest session        
        previous_start_time = contest.start_time
        previous_end_time = contest.end_time
        previous_frozen_time = contest.frozen_time
        previous_unfrozen_time = contest.unfrozen_time
        previous_user = list(contest.user.all()).copy()
        
        user_list = User.objects.filter(role__short_name='contestant').order_by('campus', 'name')

        if request.method == "POST":
            form = EditContest(request.POST, request.FILES, instance=contest)
            form.fields['user'].queryset = user_list
            if form.is_valid():
                previous_problems = list(contest.problem.all()).copy()
                post = form.save(commit=False)
                post.last_update = timezone.now()
                post.save()
                form.save_m2m()
                update_rank_score(previous_start_time, previous_end_time, previous_frozen_time,
                                previous_unfrozen_time, previous_user, previous_problems, post)
                # contset_session(post)

                messages.success(request, "The contest " +
                                contest.title+" was update successfully.")
                return redirect('site_contest_list')
        else:
            form = EditContest(instance=contest)
            form.fields['user'].queryset = user_list
        return render(request, 'site_edit_contest.html', {'form': form, "contest_id": contest.id, 'cont': 'hover'})

    else:
        total_contest = Contest.objects.all().order_by('start_time').reverse()
        now = timezone.now()
        for each_contest in total_contest:
            if each_contest.enable == False:
                each_contest.status = "disable"
            elif now < each_contest.active_time:
                each_contest.status = "not active"
            elif now < each_contest.start_time:
                each_contest.status = "active"
            elif each_contest.start_time <= now and now < each_contest.end_time:
                each_contest.status = "on going"
            elif each_contest.end_time <= now and now < each_contest.deactivate_time:
                each_contest.status = "end"
            else:
                each_contest.status = "deactivate" 
        
        return render(request, 'site_contest_detail.html', {'total_contest': total_contest,'this_contest': contest})



@login_required
@site_auth_and_contest_exist
def site_delete_contest(request, contest_id):
    refresh_contest_session_admin(request)  # refersh the contest session
    contest = Contest.objects.get(pk=contest_id)
    return render(request, 'site_delete_contest.html', {'contest': contest, 'cont': 'hover'})


@login_required
@site_auth_and_contest_exist
def site_delete_contest_done(request, contest_id):
    refresh_contest_session_admin(request)  # refersh the contest session
    contest = Contest.objects.get(pk=contest_id)
    contest.delete()
    messages.success(request, "The contest " +
                     contest.title + " was deleted successfully.")
    return redirect('site_contest_list')





@login_required
@site_auth
def site_rejudge_contest_select(request):
    now = timezone.now()
    refresh_contest_session_admin(request)  # refersh the contest session
    all_contest = Contest.objects.filter(
        start_time__lte=now, created_by=request.user.campus).order_by("start_time").reverse()

    for contest in all_contest:
        if contest.enable == False:
            contest.status = "disable"
        elif now < contest.active_time:
            contest.status = "not active"
        elif now < contest.start_time:
            contest.status = "active"
        elif contest.start_time <= now and now < contest.end_time:
            contest.status = "on going"
        elif contest.end_time <= now and now < contest.deactivate_time:
            contest.status = "end"
        else:
            contest.status = "deactivate"
    context = {'all_contest': all_contest, 'rejudge': 'hover'}
    return render(request, 'site_rejudge_select_contest.html', context)


@login_required
@site_auth_and_contest_exist
def site_rejudge_submission_list(request, contest_id):
    refresh_contest_session_admin(request)  # refersh the contest session
    contest = Contest.objects.get(pk=contest_id)

    submission_list = Submit.objects.filter(
        contest=contest).order_by('submit_time').reverse()
    all_problems = set()

    start_time = contest.start_time
    for i in submission_list:
        i.contest_time = i.submit_time - start_time
    for submit in submission_list:
        pro = (submit.problem.id, submit.problem.title)
        all_problems.add(pro)
    all_problems = sorted(all_problems, key=lambda x: x[1].lower())
    context = {'submission_list': submission_list, "contest_title": contest.title,
               'all_problems': all_problems, 'contest_id': contest.pk, 'rejudge': 'hover'}
    return render(request, 'site_rejudge_submission_list.html', context)


@login_required
@site_auth
def site_rejudge_submission_filter(request):
    refresh_contest_session_admin(request)  # refersh the contest session
    problem_id = int(request.GET.get('problem_id'))
    contest_id = int(request.GET.get('contest_id'))

    try:
        contest = Contest.objects.get(pk=contest_id)
        if contest.created_by != request.user.campus:
            return redirect('homepage')
    except Contest.DoesNotExist:
        return redirect('homepage')
    try:
        problem_title = Problem.objects.get(pk=problem_id).title
    except Problem.DoesNotExist:
        problem_title = None
    if problem_id == 0:
        all_submissions = Submit.objects.filter(
            contest_id=contest_id).order_by('submit_time').reverse()
        problem_title = "All problems"
    else:
        all_submissions = Submit.objects.filter(
            contest_id=contest_id, problem_id=problem_id).order_by('submit_time').reverse()

    start_time = contest.start_time
    for i in all_submissions:
        i.contest_time = i.submit_time - start_time

    return render(request, 'site_rejudge_filter.html', {'submission_list': all_submissions, 'problem_title': problem_title, 'rejudge': 'hover'})


@login_required
@site_auth
def site_ajax_rejudge(request):
    refresh_contest_session_admin(request)  # refersh the contest session
    total_submits = request.GET.getlist('total_submit[]')
    contest_id = request.GET.get('contest_id')
    try:
        contest = Contest.objects.get(pk=contest_id)
        if contest.created_by != request.user.campus:
            return redirect('homepage')
    except Contest.DoesNotExist:
        return redirect('homepage')

    rejudge_submits = [int(i) for i in total_submits]
    result_dict = {}
    for submit_id in rejudge_submits:
        try:
            submit = Submit.objects.get(pk=submit_id)
            try:
                result = judge(file_name=submit.submit_file.path, problem=submit.problem,
                       language=submit.language, submit=submit, rejudge=True)
                submit.result = result
                submit.save()
                update_score_and_rank(submit)
            except ValueError:
                result = "file not found"
        except Submit.DoesNotExist:
            result = "not submitted"

        result_dict[submit_id] = submit.result
    contest.last_update = timezone.now()
    contest.save()
    response_data = {'result': result_dict}
    return JsonResponse(response_data, content_type="application/json")


@login_required
@site_auth_and_submit_exist
def site_single_rejudge(request, submit_id):
    refresh_contest_session_admin(request)  # refersh the contest session
    single_submit = Submit.objects.get(pk=submit_id)
    single_submit.contest_time = single_submit.submit_time - \
        single_submit.contest.start_time
    submit = [single_submit]

    return render(request, 'site_single_user_rejudge.html', {'submit': submit, 'contest_id': single_submit.contest.pk, 'rejudge': 'hover'})


@login_required
@site_auth
def site_multi_rejudge(request, problem_id, contest_id, user_id):
    refresh_contest_session_admin(request)  # refersh the contest session
    # contest_id = request.session.get('start_contest_admin')  # ???
    current_contest = Contest.objects.get(pk=contest_id)
    submit = Submit.objects.filter(contest_id=contest_id, problem_id=problem_id, user_id=user_id,
                                   submit_time__gte=current_contest.start_time, submit_time__lte=current_contest.end_time).order_by('submit_time')
    if not submit:
        return redirect('homepage')
    specific_submissions = list()
    for i in submit:
        if i.result == 'Correct':
            specific_submissions.append(i)
            break
        else:
            specific_submissions.append(i)
    start_time = current_contest.start_time
    for i in specific_submissions:
        i.contest_time = i.submit_time - start_time

    return render(request, 'site_single_user_rejudge.html', {'submit': specific_submissions, 'contest_id': specific_submissions[0].contest.pk, 'rejudge': 'hover'})
