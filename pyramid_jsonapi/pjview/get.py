from .. import pjview
from pyramid_jsonapi.results import Results

def initial_query(view):
    return view.single_item_query()

def execute_query(view, query):
    return Results(is_collection=False, data=view.single_result(query))
