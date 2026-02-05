"""
Представления (views) для системы онбординга
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, time
from django.contrib import messages
from .models import OnboardingDay, OnboardingMaterial, InternReport


class OnboardingDayListView(LoginRequiredMixin, ListView):
    """
    Список всех дней онбординга
    """
    model = OnboardingDay
    template_name = 'onboarding/day_list.html'
    context_object_name = 'days'

    def get_queryset(self):
        """Получить только активные дни"""
        return OnboardingDay.objects.filter(is_active=True).order_by('position', 'day_number')


class OnboardingDayDetailView(LoginRequiredMixin, DetailView):
    """
    Детальная страница дня онбординга с переключением между блоками
    Онбординг/Отчёт
    """
    model = OnboardingDay
    template_name = 'onboarding/day_detail.html'
    context_object_name = 'day'
    slug_field = 'day_number'
    slug_url_kwarg = 'day_number'

    def get_object(self):
        """Получить день по номеру"""
        day_number = self.kwargs.get('day_number')
        return get_object_or_404(OnboardingDay, day_number=day_number, is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Получить все материалы для этого дня
        context['materials'] = self.object.get_active_materials()

        # Проверить, отправил ли пользователь отчёт за этот день
        # TODO: Заменить на настоящую проверку с user когда будет модель пользователя
        # user_report = InternReport.objects.filter(
        #     onboarding_day=self.object,
        #     user=self.request.user
        # ).first()
        # context['user_report'] = user_report

        # Временная заглушка
        context['user_report'] = None

        # Проверить дедлайн
        context['deadline_passed'] = self.is_deadline_passed()

        # Получить следующий и предыдущий день
        context['next_day'] = OnboardingDay.objects.filter(
            day_number__gt=self.object.day_number,
            is_active=True
        ).order_by('day_number').first()

        context['previous_day'] = OnboardingDay.objects.filter(
            day_number__lt=self.object.day_number,
            is_active=True
        ).order_by('-day_number').first()

        return context

    def is_deadline_passed(self):
        """Проверить, прошёл ли дедлайн"""
        current_time = timezone.now().time()
        deadline = self.object.deadline_time
        return current_time > deadline


class SubmitReportView(LoginRequiredMixin, CreateView):
    """
    Отправка отчёта стажёром
    """
    model = InternReport
    fields = ['report_text']
    template_name = 'onboarding/submit_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        day_number = self.kwargs.get('day_number')
        context['day'] = get_object_or_404(OnboardingDay, day_number=day_number, is_active=True)
        return context

    def form_valid(self, form):
        """Обработка формы отправки отчёта"""
        day_number = self.kwargs.get('day_number')
        onboarding_day = get_object_or_404(OnboardingDay, day_number=day_number, is_active=True)

        # Создать отчёт
        report = form.save(commit=False)
        report.onboarding_day = onboarding_day
        # TODO: Добавить пользователя когда будет модель User
        # report.user = self.request.user

        # Проверить, не опоздал ли стажёр
        current_time = timezone.now().time()
        deadline = onboarding_day.deadline_time
        report.is_late = current_time > deadline

        report.save()

        # Сообщение пользователю
        if report.is_late:
            messages.warning(
                self.request,
                f'Отчёт отправлен, но с опозданием. Дедлайн был в {deadline.strftime("%H:%M")}'
            )
        else:
            messages.success(
                self.request,
                'Отчёт успешно отправлен!'
            )

        return redirect('onboarding:day_detail', day_number=day_number)


# API представления для динамического переключения контента

def get_onboarding_content(request, day_number):
    """
    API для получения контента блока "Онбординг"
    Возвращает JSON с информацией о дне
    """
    day = get_object_or_404(OnboardingDay, day_number=day_number, is_active=True)
    materials = day.get_active_materials()

    materials_data = []
    for material in materials:
        material_dict = {
            'id': str(material.id),
            'type': material.type,
            'title': material.title,
            'content': material.content,
            'position': material.position,
        }

        # Добавить URL для файлов и изображений
        if material.file:
            material_dict['file_url'] = material.file.url

        # Добавить видео URL
        if material.type == 'video':
            if material.is_youtube_video():
                material_dict['embed_url'] = material.get_youtube_embed_url()
                material_dict['video_type'] = 'youtube'
            elif material.is_vimeo_video():
                material_dict['embed_url'] = material.get_vimeo_embed_url()
                material_dict['video_type'] = 'vimeo'
            elif material.video_url:
                material_dict['video_url'] = material.video_url
                material_dict['video_type'] = 'other'

        materials_data.append(material_dict)

    data = {
        'day_number': day.day_number,
        'title': day.title,
        'description': day.description,
        'instructions': day.instructions,
        'deadline_time': day.deadline_time.strftime('%H:%M'),
        'materials': materials_data,
    }

    return JsonResponse(data)


def get_report_form(request, day_number):
    """
    API для получения формы отчёта
    """
    day = get_object_or_404(OnboardingDay, day_number=day_number, is_active=True)

    # Проверить, отправлял ли пользователь отчёт
    # TODO: Добавить проверку с реальным пользователем
    # user_report = InternReport.objects.filter(
    #     onboarding_day=day,
    #     user=request.user
    # ).first()

    user_report = None

    # Проверить дедлайн
    current_time = timezone.now().time()
    deadline_passed = current_time > day.deadline_time

    data = {
        'day_number': day.day_number,
        'title': day.title,
        'deadline_time': day.deadline_time.strftime('%H:%M'),
        'deadline_passed': deadline_passed,
        'report_submitted': user_report is not None,
    }

    if user_report:
        data['report'] = {
            'text': user_report.report_text,
            'submitted_at': user_report.submitted_at.strftime('%d.%m.%Y %H:%M'),
            'is_late': user_report.is_late,
            'reviewed': user_report.reviewed,
            'review_comment': user_report.review_comment,
        }

    return JsonResponse(data)


def submit_report_ajax(request, day_number):
    """
    AJAX отправка отчёта
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Метод должен быть POST'}, status=405)

    day = get_object_or_404(OnboardingDay, day_number=day_number, is_active=True)
    report_text = request.POST.get('report_text', '').strip()

    if not report_text:
        return JsonResponse({'success': False, 'error': 'Текст отчёта не может быть пустым'}, status=400)

    # Проверить, не отправлял ли уже отчёт
    # TODO: Добавить проверку с реальным пользователем
    # existing_report = InternReport.objects.filter(
    #     onboarding_day=day,
    #     user=request.user
    # ).exists()
    #
    # if existing_report:
    #     return JsonResponse({'success': False, 'error': 'Вы уже отправили отчёт за этот день'}, status=400)

    # Создать отчёт
    current_time = timezone.now().time()
    is_late = current_time > day.deadline_time

    report = InternReport.objects.create(
        onboarding_day=day,
        # user=request.user,  # TODO: Добавить когда будет модель User
        report_text=report_text,
        is_late=is_late
    )

    return JsonResponse({
        'success': True,
        'message': 'Отчёт успешно отправлен!' if not is_late else 'Отчёт отправлен с опозданием',
        'is_late': is_late,
        'submitted_at': report.submitted_at.strftime('%d.%m.%Y %H:%M')
    })