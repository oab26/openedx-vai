import io
import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

about = {}
with io.open(os.path.join(here, "tutorvai", "__about__.py"), "rt", encoding="utf-8") as f:
    exec(f.read(), about)

setup(
    name="tutor-vai",
    version=about["__version__"],
    description="VAI (Veterinary Academy International) theme for Open edX",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=["tutor>=18.0.0,<21.0.0", "tutor-mfe>=18.0.0,<21.0.0"],
    entry_points={"tutor.plugin.v1": ["vai = tutorvai.plugin"]},
)
