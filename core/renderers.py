from collections import OrderedDict

from rest_framework.renderers import JSONRenderer


class UnifiedEnvelopeRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        view = renderer_context.get("view") if renderer_context else None
        if view and hasattr(view, "dont_wrap_response") and view.dont_wrap_response:
            return super().render(data, accepted_media_type, renderer_context)

        if data and isinstance(data, dict) and "success" in data:
            return super().render(data, accepted_media_type, renderer_context)

        response = renderer_context.get("response") if renderer_context else None
        status_code = response.status_code if response else 200
        is_success = 200 <= status_code < 300

        if is_success and isinstance(data, dict):
            envelope = OrderedDict([
                ("success", True),
                ("message", None),
                ("data", data.get("results", data)),
                ("meta", data.get("meta", None)),
                ("errors", None),
            ])
        elif is_success and isinstance(data, list):
            envelope = OrderedDict([
                ("success", True),
                ("message", None),
                ("data", data),
                ("meta", None),
                ("errors", None),
            ])
        else:
            return super().render(data, accepted_media_type, renderer_context)

        return super().render(envelope, accepted_media_type, renderer_context)
