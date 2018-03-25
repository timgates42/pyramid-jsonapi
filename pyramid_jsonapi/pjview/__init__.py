from functools import wraps
from collections import deque

def view_attr(stage_handlers):
    @wraps(func)
    def wrapper(func):
        def new_func(view):
            # Build a set of expected responses.
            ep_dict = view.api.endpoint_data.endpoints
            # Get route_name from route
            _, _, endpoint = view.request.matched_route.name.split(':')
            http_method = view.request.method
            responses = set(
                ep_dict['responses'].keys() |
                ep_dict['endpoints'][endpoint]['responses'].keys() |
                ep_dict['endpoints'][endpoint]['http_methods'][http_method]['responses'].keys()
            )

            try:
                request = view.execute_stage(view_method, 'request', view.request)
                view.request = request
                query = getattr(view, '{}_initial_query'.format(view_method))()
                query = view.execute_stage(view_method, 'query', query)
                results = getattr(view, '{}_execute_query'.format(view_method))(query)
                results = view.execute_stage(view_method, 'results', results)
                related_queries = view.initial_related_queries(results)
                related_queries = view.execute_stage(view_method, 'related_queries', related_queries)
                view.add_related_results(results, related_queries)
                document = view.serialise_results(results)
                document = view.execute_stage(view_method, 'document', document)
            except Exception as exc:
                if exc.__class__ not in responses:
                    logging.exception(
                        "Invalid exception raised: %s for route_name: %s path: %s",
                        exc.__class__,
                        view.request.matched_route.name,
                        view.request.current_route_path()
                    )
                    if hasattr(exc, 'code'):
                        if 400 <= exc.code < 500:  # pylint:disable=no-member
                            raise HTTPBadRequest("Unexpected client error: {}".format(exc))
                    else:
                        raise HTTPInternalServerError("Unexpected server error.")
                raise

            # Log any responses that were not expected.
            response_class = status_map[view.request.response.status_code]
            if response_class not in responses:
                logging.error(
                    "Invalid response: %s for route_name: %s path: %s",
                    response_class,
                    view.request.matched_route.name,
                    view.request.current_route_path()
                )
            return document.as_dict()

            # Instantiate stage deques and add them as attributes of new_func.
            for stage in method_stages:
                setattr(new_func, stage, deque())
            # Add any stage_handlers to appropriate deques.
            for stage, handlers in stage_handlers.items():
                for handler in handlers:
                    getattr(new_func, stage).append(handler)
        return new_func

def execute_stage(self, method, stage, arg):
    for handler in view.stages['{}_{}'.format(method, stage)]:
        arg = handler(view, arg)
    return arg

def initial_related_queries(view, results):
    rq = {}
    return rq

def add_related_results(view, results, related_queries):
    pass

def serialise_results(view, results):
    doc = pyramid_jsonapi.jsonapi.Document()
    return doc
