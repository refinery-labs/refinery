def get_go_112_base_code(app_config, code):
    code = code + "\n\n" + app_config.get("LAMDBA_BASE_CODES")["go1.12"]
    return code
