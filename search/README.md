# Vector Search with Neptune Analytics and Bedrock

This directory contains vector search implementation using Neptune Analytics and AWS Bedrock embeddings.

## Files

- `vector_search.py` - Main vector search implementation
- `test_vector_search.py` - Test script with example queries
- `visualize_search.py` - Graph visualization for search results
- `demo_visualization.py` - Visualization demo script
- `search.ipynb` - Jupyter notebook for interactive testing

## Prerequisites

1. Neptune Analytics graph must be populated with movie data
2. Movies must have embeddings (run `data_to_embedding_fast.py` first)
3. AWS credentials configured with access to:
   - Neptune Analytics
   - Bedrock (us-west-2 region)
4. Python packages for visualization:
   ```bash
   pip install pyvis
   ```

## Usage

### Basic Usage

```python
from vector_search import VectorSearch

# Initialize
search = VectorSearch(bedrock_region='us-west-2')

# Check vector index
search.create_or_reset_vector_index()

# Perform search
query = "A movie about organized crime and family"
results = search.perform_vector_search(query, top_k=3)
```

### Using Cypher Directly

```python
# Use Cypher query directly
results = search.perform_vector_search_cypher(query, top_k=5)
```

### Vector Search with Graph Hop

Perform vector search and explore graph relationships (genres, actors, directors, etc.):

```python
# 1-Hop: Get movie with related entities (genres, actors, directors, production companies)
results = search.perform_vector_search_with_hop(query, top_k=3, hop_depth=1)

# 2-Hop: Also get related movies through shared actors
results = search.perform_vector_search_with_hop(query, top_k=3, hop_depth=2)
```

### Run Main Script

```bash
cd /home/ec2-user/strandtest/search
python vector_search.py
```

### Run Tests

```bash
python test_vector_search.py
```

### Graph Visualization

Visualize search results as interactive HTML graphs:

```python
from visualize_search import SearchVisualizer

visualizer = SearchVisualizer(bedrock_region='us-west-2')

# 1-Hop visualization (movie + genres, actors, directors, companies)
visualizer.visualize_search_results(
    query="A crime family drama",
    top_k=3,
    output_file="search_result.html",
    open_browser=True
)

# 2-Hop visualization (includes related movies through actors)
visualizer.visualize_2hop_search(
    query="A crime family drama",
    top_k=2,
    output_file="search_2hop.html",
    open_browser=True
)
```

### Run Visualization Demo

```bash
# Run all demos
python demo_visualization.py

# Run specific demo
python demo_visualization.py basic    # Basic visualization
python demo_visualization.py 2hop     # 2-hop visualization
python demo_visualization.py custom   # Custom query input
```

## How It Works

1. **Query Embedding**: Converts search query to vector using Bedrock Titan embeddings (1024 dimensions)
2. **Neptune Vector Index**: Uses Neptune Analytics native vector search with `neptune.algo.vectors.topKByEmbedding`
3. **Similarity Scoring**: Neptune automatically calculates similarity scores using its vector index
4. **Ranking**: Returns top-K most similar movies based on similarity score

## Vector Search Queries

### Basic Vector Search

```cypher
CALL neptune.algo.vectors.topKByEmbedding(
    [embedding_vector],
    {topK: 3, concurrency: 4}
)
YIELD node, score
WHERE node:Movie
RETURN node.title as title,
       node.overview as overview,
       node.release_date as release_date,
       score
ORDER BY score DESC
```

### Vector Search with 1-Hop

```cypher
CALL neptune.algo.vectors.topKByEmbedding([embedding_vector], {topK: 3, concurrency: 4})
YIELD node, score
WHERE node:Movie
WITH node as movie, score
OPTIONAL MATCH (movie)-[:HAS_GENRE]->(g:Genre)
OPTIONAL MATCH (actor:Actor)-[:ACTED_IN]->(movie)
OPTIONAL MATCH (director:Director)-[:DIRECTED]->(movie)
OPTIONAL MATCH (movie)-[:PRODUCED_BY]->(pc:ProductionCompany)
RETURN movie.title, movie.overview, score,
       collect(DISTINCT g.genre_name) AS genres,
       collect(DISTINCT actor.name)[..5] AS top_actors,
       collect(DISTINCT director.name) AS directors,
       collect(DISTINCT pc.company_name)[..3] AS production_companies
ORDER BY score DESC
```

### Vector Search with 2-Hop

```cypher
CALL neptune.algo.vectors.topKByEmbedding([embedding_vector], {topK: 3, concurrency: 4})
YIELD node, score
WHERE node:Movie
WITH node as movie, score
OPTIONAL MATCH (movie)-[:HAS_GENRE]->(g:Genre)
OPTIONAL MATCH (actor:Actor)-[:ACTED_IN]->(movie)
OPTIONAL MATCH (director:Director)-[:DIRECTED]->(movie)
OPTIONAL MATCH (actor)-[:ACTED_IN]->(related_movie:Movie)
WHERE related_movie <> movie
RETURN movie.title, score,
       collect(DISTINCT g.genre_name) AS genres,
       collect(DISTINCT actor.name)[..5] AS top_actors,
       collect(DISTINCT director.name) AS directors,
       collect(DISTINCT related_movie.title)[..5] AS related_movies_by_actors
ORDER BY score DESC
```

**Important**: Neptune Analytics requires a vector index to be configured on the graph with 1024 dimensions (matching Bedrock Titan v2 embeddings).

## Graph Schema

The movie graph has the following structure:

```
(Movie)-[:HAS_GENRE]->(Genre)
(Actor)-[:ACTED_IN]->(Movie)
(Director)-[:DIRECTED]->(Movie)
(Producer)-[:PRODUCED]->(Movie)
(Movie)-[:PRODUCED_BY]->(ProductionCompany)
(Movie)-[:PRODUCED_IN]->(Country)
(Movie)-[:HAS_LANGUAGE]->(SpokenLanguage)
(User)-[:RATED]->(Movie)
```

## Example Output

### Basic Vector Search

```
🔍 벡터 검색 수행: 'The aging patriarch of an organized crime dynasty...'
   Top-K: 3

📊 검색 결과 (3개):
================================================================================
Title: The Godfather (1972-03-14)
Overview: Spanning the years 1945 to 1955, a chronicle of the fictional...
Score: 0.9234
--------------------------------------------------------------------------------
```

### Vector Search with 1-Hop

```
🔍 벡터 검색 + 1-Hop 그래프 탐색: 'organized crime family drama'

📊 검색 결과 (3개) with 1-Hop:
================================================================================

1. The Godfather (1972-03-14)
   Score: 0.9234
   Runtime: 175 min
   Genres: Crime, Drama
   Directors: Francis Ford Coppola
   Top Actors: Marlon Brando, Al Pacino, James Caan, Robert Duvall, Diane Keaton
   Production: Paramount Pictures, Alfran Productions
   Overview: Spanning the years 1945 to 1955, a chronicle of the fictional...
--------------------------------------------------------------------------------
```

### Vector Search with 2-Hop

```
🔍 벡터 검색 + 2-Hop 그래프 탐색: 'organized crime family drama'

📊 검색 결과 (2개) with 2-Hop:
================================================================================

1. The Godfather (1972-03-14)
   Score: 0.9234
   Runtime: 175 min
   Genres: Crime, Drama
   Directors: Francis Ford Coppola
   Top Actors: Marlon Brando, Al Pacino, James Caan, Robert Duvall, Diane Keaton
   Production: Paramount Pictures
   Related Movies (by actors): The Godfather: Part II, Scarface, Heat, Apocalypse Now
   Overview: Spanning the years 1945 to 1955, a chronicle of the fictional...
--------------------------------------------------------------------------------
```

## Visualization Features

### Interactive Graph Visualization

The visualization creates interactive HTML files with:

- **Color-coded nodes**:
  - 🔴 Red: Query node
  - 🔵 Blue: Movie nodes (search results)
  - 🟢 Green: Genre nodes
  - 🔴 Pink: Actor nodes
  - 🟣 Purple: Director nodes
  - 💎 Diamond: Production company nodes
  - 🟢 Light green: Related movies (2-hop)

- **Interactive features**:
  - Drag nodes to rearrange
  - Zoom in/out
  - Hover for details
  - Physics simulation for natural layout

- **Edge labels**:
  - Similarity scores (Query → Movie)
  - Relationship types (HAS_GENRE, ACTED_IN, DIRECTED, etc.)

### Visualization Output

The visualization generates HTML files that can be opened in any browser. Example structure:

```
Query → [Score] → Movie
                   ├─ HAS_GENRE → Genre
                   ├─ ACTED_IN ← Actor
                   ├─ DIRECTED ← Director
                   └─ PRODUCED_BY → Company
```

For 2-hop visualization:
```
Query → Movie ← Actor → Related Movie
```

## Notes

- Neptune Analytics automatically manages vector indices
- Embedding dimension: 1024 (Titan v2 model)
- Supports both English and Korean queries
- Visualization requires `pyvis` package
- Generated HTML files are self-contained and portable
