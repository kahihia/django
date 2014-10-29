from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseRedirect
from django.utils.http import is_safe_url
from django.views.generic import View

from brambling.models import Event, Order
from brambling.views.utils import get_dwolla


class DwollaConnectView(View):
    def get_object(self):
        raise NotImplementedError

    def get_success_url(self):
        raise NotImplementedError

    def get_redirect_url(self):
        raise NotImplementedError

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        dwolla = get_dwolla()
        client = dwolla.DwollaClientApp(settings.DWOLLA_APPLICATION_KEY,
                                        settings.DWOLLA_APPLICATION_SECRET)
        redirect_url = self.object.get_dwolla_connect_url()
        qs = request.GET.copy()
        del qs['code']
        if qs:
            redirect_url += "?"
            for k, v in qs.items():
                redirect_url += k + "=" + v
        token = client.get_oauth_token(request.GET['code'],
                                       redirect_uri=request.build_absolute_uri(redirect_url))

        self.object.dwolla_access_token = token

        # Now get account info.
        dwolla_user = dwolla.DwollaUser(token)
        self.object.dwolla_user_id = dwolla_user.get_account_info()['Id']
        self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class EventDwollaConnectView(DwollaConnectView):
    def get_object(self):
        try:
            return Event.objects.get(slug=self.kwargs['slugs'])
        except Event.DoesNotExist:
            raise Http404

    def get_success_url(self):
        return reverse('brambling_event_update',
                       kwargs={'slug': self.object.slug})


class UserDwollaConnectView(DwollaConnectView):
    def get_object(self):
        if not self.request.user.is_authenticated():
            raise Http404
        return self.request.user

    def get_success_url(self):
        request = self.request
        if ('next_url' in request.GET and
                is_safe_url(url=request.GET['next_url'],
                            host=request.get_host())):
            return request.GET['next_url']
        return reverse('brambling_user_profile')


class OrderDwollaConnectView(DwollaConnectView):
    def get_object(self):
        try:
            return Order.objects.get(code=self.kwargs['code'],
                                     event__slug=self.kwargs['event_slug'])
        except Order.DoesNotExist:
            raise Http404

    def get_success_url(self):
        return reverse('brambling_event_order_summary',
                       kwargs={'event_slug': self.object.event.slug,
                               'code': self.object.code})