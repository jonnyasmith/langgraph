import router


def test_the_router_package_imports_without_a_model_or_a_key() -> None:
    assert router.__doc__ is not None
