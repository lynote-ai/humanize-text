from setuptools import setup, find_packages

setup(
    name="humanize-text",
    version="1.5.2",
    description="Production-ready AI text humanization pipeline (DeepSeek + multi-engine translation chain)",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Lynote.ai",
    author_email="contact@lynote.ai",
    url="https://github.com/lynote-ai/humanize-text",
    project_urls={
        "Homepage": "https://lynote.ai",
        "Documentation": "https://github.com/lynote-ai/humanize-text/tree/main/docs",
        "Bug Tracker": "https://github.com/lynote-ai/humanize-text/issues",
        "Changelog": "https://github.com/lynote-ai/humanize-text/blob/main/CHANGELOG.md",
    },
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "httpx>=0.25.0",
        "toml>=0.10.2",
        "click>=8.1.0",
        "rich>=13.7.0",
        "deep-translator>=1.11.0",
        "fastapi>=0.109.0",
        "uvicorn[standard]>=0.27.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "legacy": [
            # v1.0 methodology reference implementations (Method 3 detectors)
            "transformers>=4.36.0",
            "torch>=2.1.0",
            "nltk>=3.8.0",
            "langdetect>=1.0.9",
        ],
    },
    entry_points={
        "console_scripts": [
            "humanize-text=src.standard.pipeline:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Text Processing :: Linguistic",
    ],
    keywords="ai humanize text rewriting nlp detection paraphrase deepseek",
    license="MIT",
)
