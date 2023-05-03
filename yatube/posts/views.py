from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page

from .forms import PostForm, CommentForm
from .models import Post, Group, User, Follow


def page_get(post, request):
    paginator = Paginator(post, settings.NUMBERS_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


@cache_page(20)
def index(request):
    template = 'posts/index.html'
    post = Post.objects.all()
    page_obj = page_get(post, request)
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts = group.group_posts.all()
    page_obj = page_get(posts, request)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    author = get_object_or_404(User, username=username)
    posts = author.author_posts.all()
    page_obj = page_get(posts, request)
    following = (request.user.is_authenticated
                 and Follow.objects.filter(
                     user=request.user,
                     author=author).exists())
    context = {
        'author': author,
        'page_obj': page_obj,
        'following': following,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    context = {
        'post': post,
        'form': form
    }
    return render(request, template, context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    template = 'posts/post_create.html'
    context = {
        'form': form,
    }
    if not form.is_valid():
        return render(request, template, context)
    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', request.user)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    template = 'posts/post_create.html'
    is_edit = 'используй меня полностью'
    context = {
        'post': post,
        'form': form,
        'is_edit': is_edit
    }
    if not form.is_valid():
        return render(request, template, context)
    form.save()
    return redirect('posts:post_detail', post_id)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    template = 'posts/follow.html'
    posts_list = Post.objects.filter(author__following__user=request.user)
    page_obj = page_get(posts_list, request)
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    Follow.objects.filter(
        user=request.user,
        author__username=username
    ).delete()
    return redirect('posts:profile', username=username)
