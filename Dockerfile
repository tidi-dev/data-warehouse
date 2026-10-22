# The development environment for this project: Python + DuckDB + dbt + pytest.
#
# python:3.13-slim is the official Python image on a small Debian base.
# 3.13 is the newest Python that every package in requirements.txt declares
# support for (dbt-duckdb does not list 3.14 yet).
FROM python:3.13-slim

# - don't write .pyc files into the bind-mounted project folder
# - print output immediately (no buffering), so logs appear in order
# - keep pip quiet and the image small
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# All project commands run from here. compose.yaml bind-mounts the project
# folder from your computer onto this path, so the container sees your files.
WORKDIR /workspace

# Install dependencies only. The project source is NOT copied into the image;
# it arrives at runtime through the bind mount, so edits on the host are
# visible immediately without rebuilding.
COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

CMD ["bash"]
