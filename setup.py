from setuptools import setup, find_packages

setup(
    name="observability-agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "openai>=1.13.3,<2.0.0",
        "python-dotenv==1.0.0",
        "crewai>=0.11.2",
        "requests>=2.31.0",
        "PyYAML>=6.0",
        "nats-py==2.4.0",
        "urllib3>=1.26.0",
    ],
    python_requires=">=3.10",
) 