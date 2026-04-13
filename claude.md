# BTL5 - Game Development Requirements

## Game Concept
**Style:** Top-down view (Brawl Stars camera style)
**Genre:** Team-based base destruction game (3v3)
**Theme:** Military/Tactical shooter (Team Fortress 2 weapon style)

**Game Mode:** Destroy the Enemy Base
- 3v3 teams start at opposite sides
- Objective: Destroy enemy base/core
- Map has lanes/pathways (not fully separated - can move between them)
- Power-ups spawn across map (ammo, health, damage boost)
- Respawn system with cooldown

## Hero System (6 Heroes, 3 Classes)

### Class Structure
**Total Heroes:** 6 heroes divided into 3 classes (2 heroes per class)
**Key Design:** Each class uses **TF2-style weapons/equipment**
- Each class shares the same **basic weapon type**
- Each hero has **unique ability/equipment**

### Class 1: Soldier (Ranged DPS)
**Basic Weapon:** Assault Rifle / Submachine Gun
**Stats:** Medium HP, Medium Speed, Medium-Long Range
**Role:** Main damage dealer, versatile

**Hero 1 - Rifleman:**
- Weapon: Assault Rifle
- Unique Ability: **"Frag Grenade"** - Throw explosive grenade in arc

**Hero 2 - Sniper:**
- Weapon: Sniper Rifle (slower fire rate, higher damage)
- Unique Ability: Place a beacon to tele back

### Class 2: Scout (Close-range/Flanker)
**Basic Weapon:** Shotgun / SMG
**Stats:** Low HP, High Speed, Close-Medium Range
**Role:** Flanking, assassinations, mobility

**Hero 3 - Rusher:**
- Weapon: Shotgun
- Unique Ability: **"Sprint Boost"** - Dash to a direction

**Hero 4 - Spy:**
- Weapon: Knife
- Unique Ability: **"Cloak"** - Become invisible for 3 seconds

### Class 3: Heavy (Tank/Support)
**Basic Weapon:** Heavy weapons (slow but powerful)
**Stats:** High HP, Low Speed, Medium Range
**Role:** Frontline, zone control, team support

**Hero 5 - Defender:**
- Weapon: Light Machine Gun (LMG)
- Unique Ability: **"Deploy Shield"** - Place deployable cover/barrier

**Hero 6 - Demoman:**
- Weapon:  Light Machine Gun
- Unique Ability: Grenade Launcher / RPG

## Core Requirements (10 points total)

### 1. 3D Graphics (3 points)
- [ ] 3D models for characters/units
- [ ] 3D environment/map
- [ ] Camera system (top-down/isometric view)
- [ ] Basic lighting and effects

### 2. Network Multiplayer (3 points)
- [ ] Multiple players can connect and play together
- [ ] Two modes possible:
  - Cooperative (team up against enemies)
  - PvP (fight each other)
- [ ] Synchronize player positions and actions
- [ ] Handle connections and disconnections

### 3. AI + Gameplay (4 points)

#### Basic AI (1 point)
- [ ] Single player mode available
- [ ] Enemy units can move
- [ ] Enemy units can attack at basic level

#### Power-up Items (1 point)
- [ ] Collectible items on map
- [ ] Items upgrade player stats (health, damage, speed, etc.)
- [ ] Visual feedback when collecting items

#### Enemy Variety (2 points)
- [ ] Multiple enemy types with different:
  - Movement patterns
  - Attack behaviors
  - Stats (health, damage, speed)
- [ ] Examples: light units (fast, weak), heavy units (slow, strong), ranged units, etc.

## Bonus Features

### Standard Bonus
- [ ] Implement basic game cheating methods
  - Examples: god mode, speed hacks, wallhacks, item spawning

### Special Bonus
- Most impressive game gets extra course points
- Consider adding:
  - Polished visuals and effects
  - Unique gameplay mechanics
  - Advanced AI behaviors
  - Matchmaking system
  - Character abilities/skills
  - Fog of war (MOBA-style)
  - Mini-map

## MOBA-Inspired Features to Consider

### Core MOBA Elements
- [ ] Top-down camera view
- [ ] Multiple playable characters/heroes with unique abilities
- [ ] Lanes or pathways on the map
- [ ] NPC enemies (minions/creeps) that spawn periodically
- [ ] Towers or defensive structures
- [ ] Base/nexus to defend/destroy
- [ ] Level-up system during match
- [ ] Cooldown-based abilities
- [ ] Brawl Stars

### Simplified for BTL5
- Smaller map (single lane or arena)
- 2-4 players instead of 5v5
- Fewer abilities per character (2-3 instead of 4+)
- Simpler AI for NPC units
- Basic networking (no complex server architecture)

## Getting Started (No Prior Experience)

### Prerequisites & Learning Path

#### Step 1: Choose Your Game Engine (Pick ONE)

**Option A: Unity (Recommended for Beginners)**
- **Pros:** Huge community, tons of tutorials, asset store, good for 2D/3D, C# is beginner-friendly
- **Cons:** Can be overwhelming at first
- **Language:** C#
- **Best for:** This project (3D top-down shooter)

**Option B: Godot**
- **Pros:** Lightweight, free/open-source, easier to learn, built-in networking
- **Cons:** Smaller community, fewer tutorials
- **Language:** GDScript (Python-like) or C#
- **Best for:** If you want something simpler

**Option C: Unreal Engine**
- **Pros:** Amazing graphics, Blueprint (visual scripting - no code needed)
- **Cons:** Heavy software, steeper learning curve
- **Language:** C++ or Blueprint
- **Best for:** If you want the best graphics

**→ Recommendation: Start with Unity for this project**

#### Step 2: Software You Need to Install

**Essential:**
1. **Game Engine:** Unity Hub + Unity Editor (2022 LTS version)
   - Download: https://unity.com/download
   - Free for students/personal use

2. **Code Editor:** Visual Studio Code or Visual Studio Community
   - Unity usually installs Visual Studio automatically
   - VS Code: https://code.visualstudio.com/

3. **Version Control:** Git + GitHub Desktop
   - Git: https://git-scm.com/
   - GitHub Desktop: https://desktop.github.com/
   - Why: To save your work and collaborate with teammates

**Optional but Helpful:**
- **3D Modeling:** Blender (free) - if you want to create custom models
- **Image Editing:** GIMP (free) or Photoshop
- **Sound Editing:** Audacity (free)

#### Step 3: Learning Resources (2-3 Weeks Before Starting)

**For Unity Beginners:**

**Week 1: Unity Basics (15-20 hours)**
- [ ] Unity's Official Tutorial: "Create with Code"
  - https://learn.unity.com/course/create-with-code
- [ ] Brackeys YouTube: "How to make a Video Game - Unity Beginner Tutorial"
  - https://www.youtube.com/watch?v=j48LtUkZRjU&list=PLPV2KyIb3jR5QFsefuO2RlAgWEz6EvVi6

**Week 2: C# Programming Basics (10-15 hours)**
- [ ] C# Fundamentals for Unity
  - https://learn.unity.com/tutorial/c-programming-for-unity
- [ ] Variables, Functions, If statements, Loops
- [ ] Classes and Objects (basic understanding)

**Week 3: 3D Game Specific (15-20 hours)**
- [ ] Unity Official: "Unity Tanks Tutorial"
  - https://learn.unity.com/project/tanks-tutorial
  - **THIS IS PERFECT FOR YOUR PROJECT** - It's literally a top-down combat game!
- [ ] Movement and Camera controls
- [ ] Shooting mechanics

**Networking Basics (Learn while building):**
- [ ] Unity Multiplayer Networking Tutorial
  - Search: "Mirror Networking Unity Tutorial" on YouTube
  - Or: "Unity Netcode for GameObjects Tutorial"

#### Step 4: Asset Resources (No Need to Create Everything)

**Free 3D Models:**
- **Unity Asset Store:** https://assetstore.unity.com/ (filter by "Free")
- **Mixamo:** https://www.mixamo.com/ (Free characters + animations)
- **Kenney.nl:** https://kenney.nl/ (Free game assets)
- **Sketchfab:** https://sketchfab.com/ (Many free models)
- **OpenGameArt:** https://opengameart.org/

**Free Sounds:**
- **Freesound:** https://freesound.org/
- **Mixkit:** https://mixkit.co/free-sound-effects/
- **Zapsplat:** https://www.zapsplat.com/

**Free Music:**
- **Incompetech:** https://incompetech.com/
- **Purple Planet:** https://www.purple-planet.com/

#### Step 5: Recommended Learning Timeline

**Before Starting Project (3-4 weeks):**
```
Week 1: Unity basics + C# basics (20-25 hours)
Week 2: Unity Tanks Tutorial (15-20 hours)
Week 3: Experiment and build mini-projects (10-15 hours)
Week 4: Learn networking basics (10-15 hours)
```

**During Project (2 weeks):**
```
Week 1: Build core mechanics (30-40 hours)
Week 2: Networking + polish (30-40 hours)
```

### First Steps Checklist

- [ ] Install Unity Hub and Unity Editor (2022 LTS)
- [ ] Install Visual Studio Code or Visual Studio
- [ ] Create Unity account
- [ ] Complete "Create with Code" course (at least first 2 units)
- [ ] Follow Unity Tanks Tutorial completely
- [ ] Set up GitHub repository for your project
- [ ] Download free asset packs for soldiers/weapons
- [ ] Gather your team and assign roles

### Team Role Suggestions (3-4 people)

**If 3 people:**
- **Person 1:** Gameplay programmer (movement, shooting, abilities)
- **Person 2:** Network programmer + UI
- **Person 3:** Map design, asset integration, VFX/sounds

**If 4 people:**
- **Person 1:** Gameplay programmer (heroes, combat)
- **Person 2:** Network programmer
- **Person 3:** UI/UX designer + HUD programmer
- **Person 4:** Level design, asset integration, polish

**Everyone should:**
- Learn Unity basics together
- Know C# fundamentals
- Test and debug together

## Technical Stack (After Learning)

### Game Engines
- **Unity** - Good 3D support, easy networking with Mirror/Netcode
- **Unreal Engine** - Powerful graphics, Blueprint visual scripting
- **Godot** - Lightweight, open-source, built-in networking

### Networking Solutions
- Unity: Mirror, Netcode for GameObjects, Photon
- Unreal: Built-in replication system
- Godot: Built-in high-level networking

## Implementation Phases (2-Week Timeline)

### Week 1: Foundation & Single Player

**Core Setup**
- [ ] 3D arena map with top-down camera
- [ ] Basic movement system (WASD controls)
- [ ] Health system and damage

**Class System**
- [ ] Implement 3 basic attack types:
  - Marksman: Ranged projectile
  - Assassin: Melee/dash attack
  - Tank: Slow powerful melee
- [ ] Create 2 hero variations per class (different stats/models)
- [ ] Basic attack animations

**Abilities & AI**
- [ ] Implement 6 unique abilities (1 per hero)
- [ ] Cooldown system for abilities
- [ ] Basic enemy AI (move + attack)
- [ ] 2-3 enemy types with different behaviors
- [ ] Power-up item system (spawn, collect, apply buffs)
- [ ] Single-player mode working

### Week 2: Multiplayer & Polish

**Networking**
- [ ] Set up networking framework (Unity Mirror/Photon/Netcode)
- [ ] Synchronize player positions and actions
- [ ] 3v3 team system
- [ ] Hero selection UI
- [ ] Test with 6 players

**UI & Game Flow**
- [ ] Main menu (host/join game)
- [ ] In-game HUD (health, ability cooldown, score)
- [ ] Team selection screen
- [ ] Win/loss conditions
- [ ] Respawn system

**Polish & Testing**
- [ ] Add sound effects (attacks, abilities, hits)
- [ ] Visual effects (projectiles, ability effects, hit effects)
- [ ] Bug fixing
- [ ] Balance testing (hero stats, ability cooldowns)
- [ ] Bonus features if time permits

## Assets Needed

### 3D Models
- Player characters/tanks/heroes (3-5 types)
- Enemy units (3-5 types)
- Environment (ground, obstacles, structures)
- Items/power-ups

### Audio
- Background music
- Attack sounds
- Hit/damage sounds
- Item collection sounds
- UI sounds

### VFX
- Projectile effects
- Hit effects
- Death effects
- Power-up collection effects

## Reference Games (Simplified Scope)
- Brawl Stars (simple MOBA-like, top-down)
- Battlerite (arena MOBA)
- Unity Tanks Tutorial (basic starting point)
- Small-scale arena shooters

## Notes
- Focus on getting core requirements done first (10 points)
- Keep scope manageable - simple is better than incomplete
- Use asset stores for 3D models to save time
- Test networking early and often
- Document your AI algorithms (minimax/behavior trees)
