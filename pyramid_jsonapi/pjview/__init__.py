import importlib
import inspect
import itertools
import logging
from collections import deque
from functools import wraps

from pyramid.httpexceptions import (
    HTTPNotFound,
    HTTPForbidden,
    HTTPBadRequest,
    HTTPConflict,
    HTTPUnsupportedMediaType,
    HTTPNotAcceptable,
    HTTPError,
    HTTPFailedDependency,
    HTTPInternalServerError,
    status_map,
)

from pyramid_jsonapi.results import Results
from pyramid_jsonapi.pjview import before_all
import pyramid_jsonapi

multi_stage_names = (
    'request',
    'query',
    'results',
    'related_queries',
    'document'
)
single_stage_names = (
    'initial_query',
    'execute_query'
)


def view_attr(func):
    stage_module = importlib.import_module('pyramid_jsonapi.pjview.{}'.format(func.__name__))
    stages = {}
    for stage_name in multi_stage_names:
        stages[stage_name] = deque()
    @wraps(func)
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
            request = execute_stage(view, stages['request'], view.request)
            view.request = request
            query = stages['initial_query'](view)
            query = execute_stage(view, stages['query'], query)
            results = stages['execute_query'](view, query)
            results = execute_stage(view, stages['results'], results)
            related_queries = initial_related_queries(view, results)
            related_queries = execute_stage(view, stages['related_queries'], related_queries)
            add_related_results(view, results, related_queries)
            document = serialise_results(view, results)
            document = execute_stage(view, stages['document'], document)
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

    # Add any stage_handlers to appropriate deques.
    for module in (before_all, stage_module):
        collection = module.__dict__
        for stage_name in multi_stage_names:
            try:
                handlers = collection[stage_name]
            except KeyError:
                continue
            if callable(handlers):
                # If handlers is callable just append it (note singular).
                stages[stage_name].append(handlers)
            else:
                # handlers should be an iterable of callables. Append them.
                for handler in handlers:
                    stages[stage_name].append(handler)
        for stage_name in single_stage_names:
            try:
                handler = collection[stage_name]
            except KeyError:
                continue
                # Single stages are callables.
            stages[stage_name] = handler

    # Add stage deques/funcs as attribute of new_func.
    for stage_name in itertools.chain(multi_stage_names, single_stage_names):
        setattr(new_func, stage_name, stages[stage_name])
    return new_func

def execute_stage(view, stage, arg):
    for handler in stage:
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
