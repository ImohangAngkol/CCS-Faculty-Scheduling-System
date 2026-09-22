# Genetic Algorithm Workflow

## Purpose

The Genetic Algorithm is used to generate and optimize faculty
schedules while considering scheduling constraints and faculty
preferences.

## General Workflow

1. Load scheduling data.
2. Generate the initial population.
3. Evaluate the fitness of each chromosome.
4. Sort chromosomes according to fitness.
5. Preserve elite chromosomes.
6. Select parent chromosomes.
7. Perform crossover.
8. Apply mutation when appropriate.
9. Validate generated chromosomes.
10. Introduce fresh chromosomes.
11. Evaluate the new population.
12. Preserve the best chromosome found.
13. Repeat for the configured number of generations.
14. Return the best generated schedule.

## Chromosome

A chromosome represents a complete faculty schedule.

## Fitness

The current fitness function evaluates six soft-constraint
components:

- Subject preference
- Time preference
- Day preference
- Number of preparations
- Teaching load balance
- Daily teaching load

Lower fitness values indicate a better solution.

## Best-Ever Chromosome

The system maintains the best chromosome discovered during the
optimization process.

If a later generation produces a chromosome with a lower fitness
value, that chromosome becomes the new best solution.

The best-ever chromosome is preserved so that later generations
cannot cause the final solution to become worse.