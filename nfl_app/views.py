from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import CreateView, ListView, DetailView
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from nfl_app.models import UserProfile, Question, Answer, Tag, Vote
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly
from nfl_app.serializers import QuestionSerializer, AnswerSerializer, TagSerializer, VoteSerializer, UserSerializer


class SignupCreateView(CreateView):
    model = User
    form_class = UserCreationForm

    def get_success_url(self):
        return reverse('login')


class QuestionListView(ListView):
    model = Question


class QuestionDetailView(DetailView):
    model = Question

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['question_answers'] = Answer.objects.filter(question=self.kwargs.get('pk'))
        return context


class QuestionCreateView(CreateView):
    model = Question
    fields = ('title', 'body')

    def form_valid(self, form):
        question_object = form.save(commit=False)
        tags = self.request.POST.get('tags').split(',')
        question_object.poster = self.request.user
        question_object.save()
        if any(tags):
            for tag in tags:
                try:
                    new_tag = Tag.objects.get(name=tag)
                except ObjectDoesNotExist:
                    new_tag = Tag.objects.create(name=tag)
                question_object.tags.add(new_tag)
                question_object.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('question_detail_view', kwargs={'pk': self.object.pk})

class TagDetailView(DetailView):
    model = Tag

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tag = context['object']
        context['question_list'] = [question for question in Question.objects.all() if tag in question.tags.all()]
        return context


class AnswerCreateView(CreateView):
    model = Answer
    fields = ('body',)

    def form_valid(self, form):
        answer_object = form.save(commit=False)
        answer_object.poster = self.request.user
        answer_object.question = Question.objects.get(pk=self.kwargs.get('pk'))
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('question_detail_view', kwargs={'pk': self.kwargs.get('pk')})


class UserProfileDetailView(DetailView):
    model = UserProfile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_questions'] = Question.objects.filter(poster=context['object'].user)
        return context


def upvote_create_view(request, pk):
    voter = request.user
    answer = Answer.objects.get(pk=pk)
    value = 1
    existing_user_downvote = Vote.objects.filter(voter=voter, answer=answer, value=-1)

    if answer not in Answer.objects.filter(poster=voter):
        if existing_user_downvote:
            downvote = Vote.objects.get(voter=voter, answer=answer, value=-1)
            downvote.value = value
            downvote.save()
            voter.userprofile.score += 1
            voter.userprofile.save()
        elif not Vote.objects.filter(voter=voter, answer=answer):
            Vote.objects.create(voter=voter, answer=answer, value=value)
    return HttpResponseRedirect(reverse('question_detail_view', kwargs={'pk': answer.question.pk}))


def downvote_create_view(request, pk):
    voter = request.user
    answer = Answer.objects.get(pk=pk)
    value = -1
    existing_user_upvote = Vote.objects.filter(voter=voter, answer=answer, value=1)

    if answer not in Answer.objects.filter(poster=voter):
        if existing_user_upvote:
            upvote = Vote.objects.get(voter=voter, answer=answer, value=1)
            upvote.value = value
            upvote.save()
        elif not Vote.objects.filter(voter=voter, answer=answer):
            Vote.objects.create(voter=voter, answer=answer, value=value)
        voter.userprofile.score -= 1
        voter.userprofile.save()
    return HttpResponseRedirect(reverse('question_detail_view', kwargs={'pk': answer.question.pk}))


# Begin API endpoints
class UserCreateAPIView(generics.CreateAPIView):
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        request.data['poster'] = request.user.pk
        return super().create(request, *args, **kwargs)


class QuestionListCreateAPIView(generics.ListCreateAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def create(self, request, *args, **kwargs):
        request.data['poster'] = request.user.pk
        return super().create(request, *args, **kwargs)


class QuestionRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer


class AnswerListCreateAPIView(generics.ListCreateAPIView):
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def create(self, request, *args, **kwargs):
        request.data['poster'] = request.user.pk
        return super().create(request, *args, **kwargs)


class AnswerRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer


class TagListCreateAPIView(generics.ListCreateAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)


class TagRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class VoteListCreateAPIView(generics.ListCreateAPIView):
    queryset = Vote.objects.all()
    serializer_class = VoteSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def create(self, request, *args, **kwargs):
        request.data['voter'] = request.user.pk
        if request.data['value'] == -1:
            request.user.userprofile.score -= 1
            request.user.userprofile.save()
        return super().create(request, *args, **kwargs)


class VoteRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Vote.objects.all()
    serializer_class = VoteSerializer
