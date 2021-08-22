def validate(*parameters):
    def validate_parameters_for_decorator():
        valid_parameters = ["yandex_user", "main_bus_stop", "bus_name", "bus_stop_name", "guiding_bus_stop_name"]
        if not all(parameter in valid_parameters for parameter in parameters):
            string_with_parameters = " ".join(parameters)
            raise ValueError(f"Invalid parameters {string_with_parameters} in validate decorator")

    def decorator(method):

        def wrapper(self, *args, **kwargs):
            def is_valid():
                if all([getattr(self, parameter) for parameter in parameters]):
                    return True
                return False

            def get_message_error():
                errors = []
                for parameter in parameters:
                    if getattr(self, parameter) is None:
                        parameter_to_error = {
                            "yandex_user": "зайти в свой аккаунт яндекса",
                            "main_bus_stop": "заранее сказать какой автобус запомнить",
                            "bus_name": "сказать номер автобуса",
                            "bus_stop_name": "сказать название автобусной остановки",
                            "guiding_bus_stop_name": "сказать название автобусной остановки в сторону которой будет "
                                                     "ехать автобус",
                        }
                        errors.append(parameter_to_error[parameter])
                return "Извините, для этого вы должны " + errors_to_text(errors)

            def errors_to_text(message_errors):
                if len(message_errors) > 1:
                    return ", ".join(message_errors[:-1]) + " и " + message_errors[0]
                return message_errors[0]

            if is_valid():
                return method(self, *args, **kwargs)
            return get_message_error()

        return wrapper

    validate_parameters_for_decorator()
    return decorator
