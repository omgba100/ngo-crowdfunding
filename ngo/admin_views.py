# ngo/admin_views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Message
from .forms import MessageForm

User = get_user_model()


@staff_member_required
def admin_reply_message(request, pk):
    """Vue spéciale pour que l’administrateur réponde depuis le dashboard Django"""
    original = get_object_or_404(Message, pk=pk)

    if request.method == 'POST':
        form = MessageForm(request.POST, sender=request.user)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.sender = request.user
            reply.recipient = original.sender
            reply.subject = f"RE: {original.subject}"
            reply.save()

            # Marque le message original comme lu
            original.is_read = True
            original.save(update_fields=['is_read'])

            # ✅ Redirection propre via namespace admin
            return redirect(reverse('admin:ngo_message_changelist'))
    else:
        form = MessageForm(sender=request.user)

    return render(request, 'ngo/admin/reply_message.html', {
        'form': form,
        'original': original,
        'title': _("Répondre au message"),
    })
