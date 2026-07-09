# Demo and CLI Test Questions

Use these questions to test the chatbot from the CLI, the REPL, or a live demo.
They are designed to check different behaviors: catalog lookup, transcript retrieval,
metadata lookup, synthesis across videos, and demo-friendly explanations.

```bash
uv run python backend/scripts/agent_cli.py "question"
uv run python backend/scripts/agent_cli.py              # REPL mode
```

## Quick demo path

Start here when you need a short, reliable demo flow.

1. What is FILMIG and why is it relevant to this archive?

2. How many videos are available in the archive, and what channels do they come from?

3. Which videos are from 2024?

4. What is the video "Escrituras Otras" about?

5. What does the archive say about migrant writing as a form of resistance?

## Catalog and metadata checks

Use these to verify that the agent can call catalog tools instead of only searching transcripts.

6. List all available videos with their titles and video IDs.

7. Give me the details for the video mY1hw79ydY0.

8. Which videos include identified speakers?

9. Are there videos related to Nadia Jabr? What are they about?

## Transcript retrieval checks

Use these to verify that the agent can retrieve grounded transcript evidence.

10. What does Safia El Aaddam say about racism?

11. What testimonies from Plataforma Cero discuss migration?

12. What does "writing is for the brave" mean in the context of these videos?

13. How do the testimonies describe the pain or complexity of migration?

## Cross-video synthesis checks

Use these when you want to test whether the agent can connect ideas across multiple sources.

14. Compare how FILMIG and Mujeres del Maíz use literature to make migrant voices visible.

15. What themes connect racism, migration, and self-representation across the archive?

16. How does the archive present writing: as memory, resistance, healing, or political action?

## Demo-friendly questions for a jury

Use these when the audience needs to understand the value of the system quickly.

17. If someone has never seen Plataforma Cero, what can this archive help them discover?

18. What kinds of questions can this chatbot answer better than a normal video search?

19. Why is this archive useful for researching migrant literature and antiracist narratives?

20. Show me one example where the archive connects a specific video to a broader social theme.

## Notes for interpreting results

- Catalog questions should return structured video information.
- Transcript questions should include grounded details from the source videos.
- Synthesis questions may combine several videos, so answers should explain the connection clearly.
- If an answer is vague, retry with a named video, person, year, or theme.
- This file is for manual demo and CLI testing. The formal RAGAS dataset lives in `backend/evaluation/qa_dataset.json`.
