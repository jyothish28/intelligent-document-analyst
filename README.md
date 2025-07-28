# Intelligent Document Analyst - Challenge 1B

## Project Overview

This solution addresses Challenge 1B: building an intelligent document analyst that extracts and prioritizes the most relevant sections from a collection of documents based on a specific persona and their job-to-be-done.

## Approach

1. **Document Processing**: Utilizes the PDF parsing capabilities from Challenge 1A
2. **Content Analysis**: Implements TF-IDF and semantic similarity for relevance scoring
3. **Persona-Aware Filtering**: Matches content to persona expertise and job requirements
4. **Section Prioritization**: Ranks sections based on relevance scores and importance

## Quick Start

```bash
# Build the Docker image
docker build --platform linux/amd64 -t document-analyst:v1 .

# Run the container (Linux/macOS)
docker run --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  --network none \
  document-analyst:v1

# Run the container (Windows PowerShell)
docker run --rm -v ${PWD}/input:/app/input -v ${PWD}/output:/app/output --network none document-analyst:v1

# Run the container (Windows Command Prompt)
docker run --rm -v %cd%/input:/app/input -v %cd%/output:/app/output --network none document-analyst:v1
```

## Input Structure

Place in `input/` directory:
- `documents/`: PDF files to analyze
- `config.json`: Persona and job-to-be-done specification

## Output

Generated `analysis_result.json` in `output/` directory with:
- Metadata (documents, persona, job, timestamp)
- Extracted sections with importance rankings
- Sub-section analysis with refined text
