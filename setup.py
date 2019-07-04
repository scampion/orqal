from setuptools import setup, find_packages

import orqal

setup(
    name='orqal',
    version='0.0.9',
    packages=find_packages(),
    author="Sebastien Campion",
    author_email="sebastien.campion@inria.fr",
    description="Orchestration of Algorithm on docker cluster",
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    install_requires=["aiohttp", "aiohttp-swagger", "aiohttp-jinja2", "aiohttp_utils", "pymongo==3.6.0",
                      "docker", "mongolog", "requests"],
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
