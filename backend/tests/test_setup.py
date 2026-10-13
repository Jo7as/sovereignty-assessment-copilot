def test_app_package_is_importable():
    import app

    assert app.__name__ == "app"
