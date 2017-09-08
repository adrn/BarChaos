# Third-party
import pytest

# Package
from ..config import ConfigItem, ConfigNamespace

def test_configitem():
    test = ConfigItem(15)
    test.name = 'test'
    test.set(20)

    with pytest.raises(TypeError):
        test.set(12.12)

    with pytest.raises(TypeError):
        test.set("23")

def test_confignamespace(tmpdir):

    class Config(ConfigNamespace):
        name = "test"
        derp = ConfigItem(15)

    class OtherConfig(ConfigNamespace):
        name = "another_test"
        chihei = ConfigItem("wassup", description="this is a description")

    c1 = Config()
    assert c1.derp == 15
    assert c1._items[0] == 'derp'

    c1.derp = 20
    assert c1.derp == 20

    with pytest.raises(TypeError):
        c1.derp = "20"

    c2 = Config()
    assert c2.derp == 20
    assert c2.name == c1.name

    # test saving the config to a file
    fn = str(tmpdir / 'config.yml')
    c1.save(fn)

    # test that saveing another config to the same file is ok
    c3 = OtherConfig()
    c3.save(fn)

    with open(fn) as f:
        text = f.read()

    assert ('# ' + c3._chihei.description) in text
