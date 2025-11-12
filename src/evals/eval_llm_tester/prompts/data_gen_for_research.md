# Dataset Generation Instructions for LLM Tester Agent

Generate diverse test cases that evaluate the llm_tester_agent's research capabilities and file handling.

## Test Case Requirements

### Research Query Focus
**ONLY generate World of Warcraft quest chain research queries.**

Topics to include:
- **Legendary Quest Chains**: Epic multi-patch quest lines (e.g., Legendary cloak, ring, or weapon quests)
- **Zone Quest Chains**: Major storylines within specific zones (e.g., Drustvar, Nazmir, Revendreth)
- **Campaign Quests**: Expansion-wide campaign narratives (e.g., War Campaign, Covenant Campaign)
- **Class Quest Chains**: Class hall campaigns and class-specific storylines
- **Raid-Related Quests**: Quest chains leading to or following major raids
- **Faction Quest Chains**: Alliance or Horde specific storylines
- **Event Quest Chains**: Limited-time or seasonal quest narratives
- **Epic Storylines**: Multi-zone or cross-expansion quest arcs (e.g., Wrathgate, Broken Shore)

### Complexity Levels
- **Simple**: Single short quest chain within one zone (e.g., "Research the Daughter of the Sea quest chain in Kul Tiras")
- **Medium**: Full zone or campaign quest chain (e.g., "Research the House of Eyes quest chain in Revendreth")
- **Complex**: Multi-expansion or legendary quest lines (e.g., "Research the complete Legendary cloak quest chain from Mists of Pandaria")

### File Handling Scenarios
- **No Save**: ~40% of cases should not require file saving
- **With Filename**: ~40% should specify explicit filename in `output/eval/` folder (e.g., "output/eval/research_arthas.md")
- **Without Filename**: ~20% should request save but without filename to test agent's clarification flow
- **IMPORTANT**: All filenames must be in the `output/eval/` directory path

## Example Test Cases

### Example 1: Simple Quest Chain (No Save)
```
research_query: "Research the Daughter of the Sea quest chain in Boralus"
save_to_file: false
filename: null
complexity_level: "simple"
topic_category: "wow_quest_chain"
```

### Example 2: Medium Quest Chain (With Save)
```
research_query: "Research the Wrathgate quest chain and its impact on the Wrath of the Lich King story"
save_to_file: true
filename: "output/eval/wrathgate_quest_chain.md"
complexity_level: "medium"
topic_category: "wow_quest_chain"
```

### Example 3: Complex Quest Chain (With Save)
```
research_query: "Research the complete Legendary cloak quest chain from Mists of Pandaria with Wrathion"
save_to_file: true
filename: "output/eval/legendary_cloak_mop.md"
complexity_level: "complex"
topic_category: "wow_quest_chain"
```

## Output Quality Expectations

Each generated case should:
1. Have a clear, specific research query
2. Appropriate complexity level for the topic
3. Realistic file handling requirements
4. Diverse topic categories across the dataset
5. Balanced distribution of save/no-save scenarios
