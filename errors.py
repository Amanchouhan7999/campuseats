from flask import jsonify, make_response

def problem(type_uri, title, status, detail, errors=None):
    """
    Standardise on Problem Details error shape.
    """
    body = {
        "type": type_uri,
        "title": title,
        "status": status,
        "detail": detail
    }
    if errors:
        body["errors"] = errors
        
    response = make_response(jsonify(body), status)
    response.headers['Content-Type'] = 'application/problem+json; charset=utf-8'
    return response