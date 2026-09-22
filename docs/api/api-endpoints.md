# API Documentation

Base development URL:

http://127.0.0.1:8000

Interactive FastAPI documentation is available through `/docs`
while the backend is running.

## System

### GET /

Checks whether the API is running.

### GET /api/health

Returns the health status of the backend.

---

## Faculty

### GET /api/faculty/

Returns the available faculty data.

Database integration is not yet implemented.

### GET /api/faculty/{faculty_id}

Returns information for a specific faculty member.

---

## Genetic Algorithm

### GET /api/ga/status

Checks whether the Genetic Algorithm API is available.

### POST /api/ga/generate

Generates an initial population and returns the best generated
schedule from that population.

Query parameter:

- `population_size`

### POST /api/ga/run

Runs the complete Genetic Algorithm optimization process.

Query parameters:

- `population_size`
- `generations`
- `fresh_chromosomes`

The response contains:

- Best fitness
- Fitness breakdown
- Number of completed generations
- Population size
- Generation history
- Generated schedule