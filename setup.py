from setuptools import setup, find_packages

import orqal

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='orqal',
    version=orqal.__version__,
    packages=find_packages(),
    author="Sebastien Campion",
    author_email="sebastien.campion@inria.fr",
    description="orqal client module",
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'orqal-web = orqal.web:main',
            'orqal-worker = orqal.worker:main',
        ],
    },
    include_package_data=True,
    zip_safe=True,
    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 1 - Planning",
        "License :: OSI Approved",
        "Natural Language :: French",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Topic :: Communications",
    ],
    license="AGPL",
)
