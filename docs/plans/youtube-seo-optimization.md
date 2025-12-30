# YouTube SEO Optimization Plan

## Overview
Enhance the `youtube_metadata_agent` to generate more SEO-optimized titles, descriptions, and tags for better YouTube discoverability and engagement.

## Current State
**File:** `src/agents/youtube_metadata_agent/prompts/system_prompt.md`

The current prompt covers basic SEO but lacks several proven optimization techniques:
- Title: Basic guidelines (60 chars, power words, WoW branding)
- Description: 500 char limit with hook and hashtags
- Tags: 10-15 tags with broad/specific mix

## Proposed Changes

### 1. Title Optimization Improvements

**Add to system prompt:**
- Front-load keywords (most important words first - YouTube truncates after ~60 chars)
- Use numbers when applicable (e.g., "5 Epic Moments" - proven higher CTR)
- Include freshness signals for WoW content (patch/expansion references)
- Ensure title and story theme align for "thumbnail synergy"

### 2. Description Optimization Improvements

**Expand description strategy:**
- Increase limit from 500 to 2000 characters (YouTube allows 5000)
- Structure with clear sections:
  - Hook (first 2 lines - visible before "Show more")
  - Story summary with natural keyword integration
  - Timestamps placeholder for key moments
  - Call-to-action (like, subscribe, comment)
  - Related content links placeholder
- Limit hashtags to 3-5 (YouTube only displays 3 above title)
- Include long-tail keywords naturally in the body

### 3. Tags Optimization Improvements

**Enhance tag strategy:**
- Reduce to 8-12 tags (quality over quantity)
- Prioritize tag order (YouTube weights first tags higher):
  1. Primary target keyword
  2. Main topic variations
  3. Long-tail keywords (e.g., "world of warcraft dragonflight quest walkthrough")
  4. Supporting keywords
  5. Branded terms (WoW, World of Warcraft, Warcraft)
- Include expansion/patch-specific tags for freshness

## Implementation Steps

1. **Update system prompt** (`system_prompt.md`)
   - Restructure title section with front-loading and number guidelines
   - Expand description section with new structure and 1500-2000 char target
   - Revise tags section with priority ordering and reduced count
   - Add examples for each section

2. **Test with sample story**
   - Run agent with existing story JSON
   - Verify output quality and structure

## File to Modify

`src/agents/youtube_metadata_agent/prompts/system_prompt.md`

## Success Criteria

- Titles are front-loaded with keywords and under 60 chars
- Descriptions are 1500-2000 chars with clear structure
- Tags are ordered by priority with 8-12 quality entries
- No changes to output model (keep simple: title, description, tags)
