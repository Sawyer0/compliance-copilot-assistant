from setuptools import setup, find_packages

setup(
    name="compliance-ingestion",
    version="0.1.0",
    description="Enterprise-grade compliance document ingestion engine",
    packages=find_packages(exclude=["tests*", "outputs*", "node_modules*"]),
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "PyMuPDF>=1.23.0",
        "pdfplumber>=0.10.0",
        "trafilatura>=1.6.0",
        "markdownify>=0.11.0",
        "pytesseract>=0.3.10",
        "Pillow>=10.0.0",
        "pyyaml>=6.0",
        "pydantic>=2.0.0",
        "click>=8.1.0",
        "httpx>=0.25.0",
        "aiofiles>=23.0.0",
        "structlog>=23.0.0",
        "tenacity>=8.2.0",
        "python-dotenv>=1.0.0",
        "rich>=13.0.0",
        "inngest>=0.3.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "mypy>=1.5.0",
            "black>=23.7.0",
            "flake8>=6.0.0",
            "isort>=5.12.0",
        ]
    },
    python_requires=">=3.8",
) 