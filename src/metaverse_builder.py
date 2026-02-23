"""
Metaverse World Builder
Procedurally generates and manages metaverse worlds with SQLite persistence.
"""

import sqlite3
import argparse
import random
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Database location
DB_PATH = Path.home() / ".blackroad" / "metaverse.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

THEMES = ["cyberpunk", "fantasy", "space", "underwater", "desert", "arctic", "jungle", "neon"]
OBJECT_TYPES = ["building", "tree", "light", "terrain", "water", "vehicle", "npc", "portal", "artifact"]

THEME_COLORS = {
    "cyberpunk": "#FF00FF",
    "fantasy": "#8B4513",
    "space": "#000080",
    "underwater": "#0000CD",
    "desert": "#F4A460",
    "arctic": "#F0F8FF",
    "jungle": "#228B22",
    "neon": "#FFFF00"
}


@dataclass
class WorldObject:
    id: str
    type: str
    name: str
    x: float
    y: float
    z: float
    scale: float = 1.0
    rotation: float = 0.0
    color: str = "#FFFFFF"
    properties: Dict = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class MetaverseWorld:
    id: str
    name: str
    theme: str
    seed: int
    size: int
    objects: List[WorldObject] = None
    created_at: float = 0.0
    description: str = ""

    def __post_init__(self):
        if self.objects is None:
            self.objects = []


class MetaverseBuilder:
    def __init__(self):
        self.conn = sqlite3.connect(str(DB_PATH))
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS worlds (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                theme TEXT NOT NULL,
                seed INTEGER,
                size INTEGER,
                created_at REAL,
                description TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS world_objects (
                id TEXT PRIMARY KEY,
                world_id TEXT,
                type TEXT,
                name TEXT,
                x REAL,
                y REAL,
                z REAL,
                scale REAL,
                rotation REAL,
                color TEXT,
                properties TEXT,
                FOREIGN KEY (world_id) REFERENCES worlds(id)
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_positions (
                player_id TEXT,
                world_id TEXT,
                x REAL,
                y REAL,
                z REAL,
                teleported_at REAL,
                PRIMARY KEY (player_id, world_id)
            )
        """)
        self.conn.commit()

    def create_world(self, name: str, theme: str, seed: Optional[int] = None, size: int = 1024) -> MetaverseWorld:
        """Create a new procedurally generated world."""
        if theme not in THEMES:
            raise ValueError(f"Invalid theme. Choose from: {', '.join(THEMES)}")
        
        if seed is None:
            seed = random.randint(1, 1000000)
        
        now = datetime.now().timestamp()
        world_id = f"world_{int(now * 1000)}"
        
        self.cursor.execute(
            """INSERT INTO worlds (id, name, theme, seed, size, created_at, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (world_id, name, theme, seed, size, now, f"A {theme} metaverse world")
        )
        self.conn.commit()
        
        return MetaverseWorld(world_id, name, theme, seed, size, [], now)

    def add_object(
        self, world_id: str, type_: str, name: str, x: float, y: float, z: float,
        **props
    ) -> WorldObject:
        """Add an object to a world."""
        if type_ not in OBJECT_TYPES:
            raise ValueError(f"Invalid type. Choose from: {', '.join(OBJECT_TYPES)}")
        
        world = self.get_world(world_id)
        if not world:
            raise ValueError(f"World {world_id} not found")
        
        obj_id = f"obj_{int(datetime.now().timestamp() * 1000)}"
        scale = props.get("scale", 1.0)
        rotation = props.get("rotation", 0.0)
        color = props.get("color", THEME_COLORS.get(world.theme, "#FFFFFF"))
        properties = json.dumps({k: v for k, v in props.items() if k not in ["scale", "rotation", "color"]})
        
        self.cursor.execute(
            """INSERT INTO world_objects 
               (id, world_id, type, name, x, y, z, scale, rotation, color, properties)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (obj_id, world_id, type_, name, x, y, z, scale, rotation, color, properties)
        )
        self.conn.commit()
        
        return WorldObject(obj_id, type_, name, x, y, z, scale, rotation, color, json.loads(properties))

    def get_world(self, world_id: str) -> Optional[MetaverseWorld]:
        """Retrieve a world."""
        self.cursor.execute("SELECT * FROM worlds WHERE id = ?", (world_id,))
        row = self.cursor.fetchone()
        if row:
            world = MetaverseWorld(*row)
            # Load objects
            self.cursor.execute(
                "SELECT id, type, name, x, y, z, scale, rotation, color, properties FROM world_objects WHERE world_id = ?",
                (world_id,)
            )
            world.objects = [
                WorldObject(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], json.loads(r[9]))
                for r in self.cursor.fetchall()
            ]
            return world
        return None

    def generate_terrain(self, world_id: str):
        """Generate procedural terrain for a world."""
        world = self.get_world(world_id)
        if not world:
            raise ValueError(f"World {world_id} not found")
        
        # Use seed for reproducibility
        random.seed(world.seed)
        
        # Add terrain patches
        grid_size = int(world.size / 256)
        for i in range(0, grid_size):
            for j in range(0, grid_size):
                x = i * 256
                z = j * 256
                height = random.randint(-10, 50)
                
                self.add_object(
                    world_id, "terrain", f"terrain_{i}_{j}", x, height, z,
                    scale=256, color=self._get_terrain_color(world.theme)
                )

    def _get_terrain_color(self, theme: str) -> str:
        """Get terrain color based on theme."""
        colors = {
            "cyberpunk": "#1a1a2e",
            "fantasy": "#8B7355",
            "space": "#1a1a3a",
            "underwater": "#006994",
            "desert": "#C2B280",
            "arctic": "#FFFAFA",
            "jungle": "#355C3D",
            "neon": "#00FF00"
        }
        return colors.get(theme, "#808080")

    def populate_world(self, world_id: str):
        """Auto-populate world with objects based on theme."""
        world = self.get_world(world_id)
        if not world:
            raise ValueError(f"World {world_id} not found")
        
        random.seed(world.seed)
        
        # Add buildings
        for i in range(8):
            x = random.uniform(0, world.size)
            z = random.uniform(0, world.size)
            self.add_object(world_id, "building", f"{world.theme}_building_{i}", x, 20, z, scale=20)
        
        # Add trees (except for space/underwater themes)
        if world.theme not in ["space", "underwater"]:
            for i in range(15):
                x = random.uniform(0, world.size)
                z = random.uniform(0, world.size)
                self.add_object(world_id, "tree", f"tree_{i}", x, 5, z, scale=5)
        
        # Add lights
        for i in range(4):
            x = random.uniform(0, world.size)
            z = random.uniform(0, world.size)
            self.add_object(world_id, "light", f"light_{i}", x, 100, z, scale=2, color="#FFFF00")
        
        # Add special objects by theme
        if world.theme == "cyberpunk":
            self.add_object(world_id, "npc", f"neon_runner", 500, 50, 500, scale=2, color="#FF00FF")
        elif world.theme == "fantasy":
            self.add_object(world_id, "artifact", f"ancient_stone", 512, 20, 512, scale=10, color="#808080")
        elif world.theme == "space":
            self.add_object(world_id, "portal", f"stargate", 512, 100, 512, scale=50, color="#00FFFF")
        
        self.conn.commit()

    def export_json(self, world_id: str) -> Dict:
        """Export world as JSON (Three.js compatible format)."""
        world = self.get_world(world_id)
        if not world:
            raise ValueError(f"World {world_id} not found")
        
        objects_data = []
        for obj in world.objects:
            objects_data.append({
                "id": obj.id,
                "type": obj.type,
                "name": obj.name,
                "position": {"x": obj.x, "y": obj.y, "z": obj.z},
                "scale": obj.scale,
                "rotation": obj.rotation,
                "color": obj.color,
                "properties": obj.properties
            })
        
        return {
            "id": world.id,
            "name": world.name,
            "theme": world.theme,
            "seed": world.seed,
            "size": world.size,
            "objects": objects_data,
            "created_at": datetime.fromtimestamp(world.created_at).isoformat()
        }

    def export_gltf_stub(self, world_id: str) -> Dict:
        """Export minimal GLTF structure stub."""
        world = self.get_world(world_id)
        if not world:
            raise ValueError(f"World {world_id} not found")
        
        return {
            "asset": {"version": "2.0", "generator": "MetaverseBuilder"},
            "scene": 0,
            "scenes": [{"name": world.name, "nodes": list(range(len(world.objects)))}],
            "nodes": [
                {
                    "name": obj.name,
                    "translation": [obj.x, obj.y, obj.z],
                    "scale": [obj.scale, obj.scale, obj.scale]
                }
                for obj in world.objects
            ],
            "meshes": [{"primitives": [{"attributes": {}}]} for _ in world.objects]
        }

    def list_worlds(self) -> List[Dict]:
        """List all worlds with object counts."""
        self.cursor.execute("SELECT id, name, theme, created_at FROM worlds")
        worlds = []
        for row in self.cursor.fetchall():
            world_id, name, theme, created_at = row
            self.cursor.execute("SELECT COUNT(*) FROM world_objects WHERE world_id = ?", (world_id,))
            obj_count = self.cursor.fetchone()[0]
            worlds.append({
                "id": world_id,
                "name": name,
                "theme": theme,
                "object_count": obj_count,
                "created_at": datetime.fromtimestamp(created_at).isoformat()
            })
        return worlds

    def teleport(self, world_id: str, player_id: str, x: float, y: float, z: float):
        """Log player teleport position."""
        now = datetime.now().timestamp()
        try:
            self.cursor.execute(
                """INSERT INTO player_positions (player_id, world_id, x, y, z, teleported_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (player_id, world_id, x, y, z, now)
            )
        except sqlite3.IntegrityError:
            self.cursor.execute(
                """UPDATE player_positions SET x = ?, y = ?, z = ?, teleported_at = ?
                   WHERE player_id = ? AND world_id = ?""",
                (x, y, z, now, player_id, world_id)
            )
        self.conn.commit()

    def close(self):
        """Close database connection."""
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(description="Metaverse World Builder")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Create world
    create_parser = subparsers.add_parser("create", help="Create a new world")
    create_parser.add_argument("name", help="World name")
    create_parser.add_argument("theme", choices=THEMES, help="World theme")
    create_parser.add_argument("--seed", type=int, default=None, help="Random seed")
    
    # Populate world
    populate_parser = subparsers.add_parser("populate", help="Populate world with objects")
    populate_parser.add_argument("world_id", help="World ID")
    
    # Export
    export_parser = subparsers.add_parser("export", help="Export world")
    export_parser.add_argument("world_id", help="World ID")
    export_parser.add_argument("--format", choices=["json", "gltf"], default="json")
    
    args = parser.parse_args()
    
    builder = MetaverseBuilder()
    
    try:
        if args.command == "create":
            world = builder.create_world(args.name, args.theme, args.seed)
            builder.generate_terrain(world.id)
            print(f"✓ Created world: {world.name} ({world.theme})")
            print(f"  ID: {world.id}")
            print(f"  Seed: {world.seed}")
        
        elif args.command == "populate":
            builder.populate_world(args.world_id)
            world = builder.get_world(args.world_id)
            if world:
                print(f"✓ Populated {world.name} with {len(world.objects)} objects")
        
        elif args.command == "export":
            if args.format == "json":
                data = builder.export_json(args.world_id)
                print(json.dumps(data, indent=2)[:200] + "...")
            else:
                data = builder.export_gltf_stub(args.world_id)
                print(json.dumps(data, indent=2)[:200] + "...")
        
        else:
            worlds = builder.list_worlds()
            print(f"Worlds ({len(worlds)}):")
            for w in worlds:
                print(f"  {w['name']} ({w['theme']}) - {w['object_count']} objects")
    
    finally:
        builder.close()


if __name__ == "__main__":
    main()
