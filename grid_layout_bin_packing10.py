from pathlib import Path
import json
from PIL import Image
from natsort import natsorted

# .stop_accom, .no_accum, .grid_layout


SPRITESHEET_SIZE = 1024  * 4
SPRITE_SIZE = 64
SPRITE_PADDING = 0
SPRITES_PER_ROW = SPRITESHEET_SIZE // SPRITE_SIZE
SPRITES_PER_SHEET = SPRITES_PER_ROW * SPRITES_PER_ROW
RESIZE_METHOD = Image.NEAREST   #use Image.NEAREST for nearest neigbour algo, Image.LANCZOS for smooth interpolation
SPRITESHEET_FORMAT = 'webp'
WEBP_QUALITY = 100
WEBP_METHOD = 0
PNG_COMPRESS_LEVEL = 9
PNG_OPTIMIZE = True

SHARPEN = False
SHARPEN_RADIUS = 2
SHARPEN_PERCENT = 100
SHARPEN_THRESHOLD = 3

GAUSSIAN_BLUR = False
GAUSSIAN_BLUR_RADIUS = 2
COLOR_TO_TRANSPARENT = 'blue'
COLOR_THRESHOLD = 30

DITHERING = True
DITHER_MODE = 'custom_palette'
DITHER_METHOD = 'ordered'
DITHER_COLORS = 256
CUSTOM_PALETTE = ['#000000', '#FF0000', '#00FF00']

MAX_GIF_FRAMES = 30

STACK_SPACING = 0.15
SEED = 293 # Master seed for deterministic randomization (zoom, layout, etc)
QUICKLOAD_TRESHOLD= 293

ORDERED_GRID_LAYOUT = True

ROTATION_SPEED = 0.000015

RANDOM_TEXTDIV_POSITION = False  # False = text always left, True = random based on seed



def apply_filter(img):
    if SHARPEN:
        from PIL import ImageFilter
        img = img.filter(ImageFilter.UnsharpMask(
            radius=SHARPEN_RADIUS,
            percent=SHARPEN_PERCENT,
            threshold=SHARPEN_THRESHOLD
        )) 

    if GAUSSIAN_BLUR:
        from PIL import ImageFilter
        img = img.filter(ImageFilter.GaussianBlur(radius=GAUSSIAN_BLUR_RADIUS))
    
    if COLOR_TO_TRANSPARENT:
        colors = {
            'black': (0, 0, 0),
            'white': (255, 255, 255),
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'yellow': (255, 255, 0),
            'cyan': (0, 255, 255),
            'magenta': (255, 0, 255),
            'light_gray': (192, 192, 192),
            'dark_gray': (64, 64, 64),
            'orange': (255, 165, 0),
            'purple': (128, 0, 128)
        }
        target_r, target_g, target_b = colors[COLOR_TO_TRANSPARENT]
        img = img.convert('RGBA')
        pixels = img.load()
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = pixels[x, y]
                if (abs(r - target_r) < COLOR_THRESHOLD and 
                    abs(g - target_g) < COLOR_THRESHOLD and 
                    abs(b - target_b) < COLOR_THRESHOLD):
                    pixels[x, y] = (r, g, b, 0)
    
    if DITHERING:
        dither_map = {
            'floyd_steinberg': Image.Dither.FLOYDSTEINBERG,
            'ordered': Image.Dither.ORDERED,
            'none': Image.Dither.NONE
        }
        
        has_alpha = img.mode == 'RGBA'
        alpha_channel = img.split()[3] if has_alpha else None
        
        if DITHER_MODE == 'bw':
            rgb_img = img.convert('L')
            dithered = rgb_img.convert('1', dither=dither_map[DITHER_METHOD])
            dithered = dithered.convert('RGB')
        
        elif DITHER_MODE == 'color_reduce':
            rgb_img = img.convert('RGB')
            dithered = rgb_img.quantize(colors=DITHER_COLORS, dither=dither_map[DITHER_METHOD])
            dithered = dithered.convert('RGB')
        
        elif DITHER_MODE == 'custom_palette':
            palette_colors = []
            for hex_color in CUSTOM_PALETTE:
                hex_color = hex_color.lstrip('#')
                r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                palette_colors.extend([r, g, b])
            
            while len(palette_colors) < 768:
                palette_colors.extend([0, 0, 0])
            
            palette_img = Image.new('P', (1, 1))
            palette_img.putpalette(palette_colors)
            
            rgb_img = img.convert('RGB')
            dithered = rgb_img.quantize(palette=palette_img, dither=dither_map[DITHER_METHOD])
            dithered = dithered.convert('RGB')
        
        if has_alpha:
            dithered = dithered.convert('RGBA')
            dithered.putalpha(alpha_channel)
        
        img = dithered
    
    return img

def resize_image(img):
    w, h = img.size
    longest = max(w, h)
    if longest != SPRITE_SIZE:
        scale = SPRITE_SIZE / longest
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = img.resize((new_w, new_h), RESIZE_METHOD)
    return img

def scan_folder(path, ignore=['venv', '__pycache__', '.git', 'spritesheets', 'images', 'backup']):
    if path.name in ignore:
        return None
    
    images = []
    texts = []
    children = []
    grid_layout = None
    no_accum = False
    stop_accum = False
    
    if path.is_dir():
        grid_file = path / '.grid_layout'
        if grid_file.exists():
            grid_layout = grid_file.read_text().strip()
        
        no_accum_file = path / '.no_accum'
        no_accum = no_accum_file.exists()
        
        stop_accum_file = path / '.stop_accum'
        stop_accum = stop_accum_file.exists()
            
        for item in natsorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
            if item.name in ignore or item.name in ['.grid_layout', '.no_accum', '.stop_accum']:
                continue
            if item.is_file():
                if item.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                    images.append(str(item.relative_to('.')))
                elif item.suffix.lower() == '.html':
                    texts.append(str(item.relative_to('.')))
            elif item.is_dir():
                child = scan_folder(item, ignore)
                if child:
                    children.append(child)
        
        all_images = images.copy()
        all_texts = texts.copy()
        for child in children:
            all_images.extend(child['ai'])
            if not child.get('na', False) and not child.get('sa', False):  # check both flags
                all_texts.extend(child['at'])        
        

    
    content_type = 'empty'
    if all_images and all_texts:
        content_type = 'mixed'
    elif all_images:
        content_type = 'images'
    elif all_texts:
        content_type = 'text'
    
    result = {
        'name': path.name,
        'path': str(path.relative_to('.')),
        'type': content_type,
        'children': children,
        'ai': all_images,
        'at': all_texts,
        'oi': images,
        'ot': texts,
        'na': no_accum,
        'sa': stop_accum
    }
    
    if grid_layout:
        result['grid_layout'] = grid_layout
    
    return result

root = scan_folder(Path('.'))

all_image_paths = []
def collect_images(node):
    all_image_paths.extend(node['oi'])
    for child in node['children']:
        collect_images(child)
collect_images(root)

all_image_paths = natsorted(all_image_paths)

Path('spritesheets').mkdir(exist_ok=True)
for file in Path('spritesheets').glob('*'):
    file.unlink()

sprite_data = {}
sheet_idx = 0
slot_idx = 0
sheet = Image.new('RGBA', (SPRITESHEET_SIZE, SPRITESHEET_SIZE), (0, 0, 0, 0))

for idx, img_path in enumerate(all_image_paths):
    is_gif = img_path.lower().endswith('.gif')
    
    if is_gif:
        gif = Image.open(img_path)
        frame_count = min(gif.n_frames,MAX_GIF_FRAMES) 
        
        if slot_idx + frame_count > SPRITES_PER_SHEET:
            if slot_idx > 0:
                sheet.save(f'spritesheets/sprites_{sheet_idx}.{SPRITESHEET_FORMAT}')
            sheet_idx += 1
            slot_idx = 0
            sheet = Image.new('RGBA', (SPRITESHEET_SIZE, SPRITESHEET_SIZE), (0, 0, 0, 0))
        
        start_idx = slot_idx
        for frame_idx in range(frame_count):
            gif.seek(frame_idx)
            frame = gif.convert('RGBA')
            frame = resize_image(frame)
            frame = apply_filter(frame)           
 
            col = slot_idx % SPRITES_PER_ROW
            row = slot_idx // SPRITES_PER_ROW
            x = col * SPRITE_SIZE + SPRITE_PADDING
            y = row * SPRITE_SIZE + SPRITE_PADDING
            sheet.paste(frame, (x, y))
            slot_idx += 1
        
        sprite_data[img_path] = {
            'ss': f'spritesheets/sprites_{sheet_idx}.{SPRITESHEET_FORMAT}',
            'si': start_idx,
            'fc': frame_count,
            'anim': True,
            'w': SPRITE_SIZE,
            'h': SPRITE_SIZE,
            'gi': idx,
            'path': img_path
        }
    else:
        img = Image.open(img_path).convert('RGBA')
        img = resize_image(img)
        img = apply_filter(img)       

 
        col = slot_idx % SPRITES_PER_ROW
        row = slot_idx // SPRITES_PER_ROW
        x = col * SPRITE_SIZE + SPRITE_PADDING
        y = row * SPRITE_SIZE + SPRITE_PADDING
        sheet.paste(img, (x, y))
        
        sprite_data[img_path] = {
            'ss': f'spritesheets/sprites_{sheet_idx}.{SPRITESHEET_FORMAT}',
            'idx': slot_idx,
            'gi': idx,
            'w': img.width,
            'h': img.height,
            'path': img_path
        }
        slot_idx += 1
    
    if slot_idx >= SPRITES_PER_SHEET:
        sheet.save(f'spritesheets/sprites_{sheet_idx}.{SPRITESHEET_FORMAT}')
        sheet_idx += 1
        slot_idx = 0
        sheet = Image.new('RGBA', (SPRITESHEET_SIZE, SPRITESHEET_SIZE), (0, 0, 0, 0))

if slot_idx > 0:
    sheet.save(f'spritesheets/sprites_{sheet_idx}.{SPRITESHEET_FORMAT}')

def replace_images(node):
    node['ai'] = [sprite_data[p] for p in node['ai']]
    node['oi'] = [sprite_data[p] for p in node['oi']]
    for child in node['children']:
        replace_images(child)

replace_images(root)

sprite_config = {
    'spritesheet_size': SPRITESHEET_SIZE,
    'sprite_size': SPRITE_SIZE,
    'sprite_padding': SPRITE_PADDING,
    'sprites_per_row': SPRITES_PER_ROW,
    'stack_spacing': STACK_SPACING,
    'seed': SEED,
    'quickload_threshold': QUICKLOAD_TRESHOLD,
    'ordered_grid_layout': ORDERED_GRID_LAYOUT,
    'rotation_speed': ROTATION_SPEED,
    'random_textdiv_position': RANDOM_TEXTDIV_POSITION
}

with open('data.json', 'w') as f:
    json.dump({'tree': root, 'sprite_config': sprite_config}, f, indent=2)

with open('index.html', 'w') as f:
    f.write(f'''<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="styles.css">
<script src="https://unpkg.com/stats.js@0.17.0/build/stats.min.js"></script>
<meta charset="utf-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ 
    background: black; 
    color: white; 
    font-family: monospace; 
    font-size: 11px;
    display: flex;
    height: 100vh;
    overflow: hidden;
}}

#tree {{ 
    width: auto;
    min-width: 300px;
    max-width: 50%;
    border-right: 1px solid white; 
    overflow-y: auto; 
    padding: 10px;
}}

#content {{ 
    flex: 1; 
    display: flex;
    flex-wrap: wrap;
    overflow: hidden;
}}
.tree-item {{ white-space: pre; }}
.tree-link {{ cursor: pointer; color: #4af; }}
.tree-link:hover {{ background: #222; }}
.content-div {{
    border: 1px solid white;
    position: relative;
    overflow: hidden;
}}
.div-label {{
    position: absolute;
    top: 5px;
    left: 5px;
    background: black;
    padding: 2px 5px;
    border: 1px solid white;
    z-index: 100;
}}
.text-content {{
    padding: 20px;
    overflow-y: auto;
    white-space: pre-wrap;
}}
canvas {{ display: block; width: 100%; height: 100%; }}
</style>
</head>
<body>
<div id="tree"></div>
<div id="content"></div>
<script type="importmap">
{{
  "imports": {{
    "three": "https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/jsm/"
  }}
}}
</script>
<script type="module">
import * as THREE from 'three';
import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';

let dataTree;
let spriteConfig;
let activeScenes = [];
const spritesheets = {{}};
const pendingLoads = {{}};
const materialCache = {{}};
const geometryCache = {{}};

function seededRandom(seed) {{
        let state = seed;
        state = (state * 1664525 + 1013904223) % 4294967296;
        return state / 4294967296;
    }}


function getAllSpritesheetPaths(node, paths = new Set()) {{
    node.ai.forEach(img => paths.add(img.ss));
    node.oi.forEach(img => paths.add(img.ss));
    node.children.forEach(child => getAllSpritesheetPaths(child, paths));
    return Array.from(paths);
}}

async function preloadSpritesheets(paths) {{
    const loadProgress = document.getElementById('load-progress');
    let loaded = 0;
    
    const promises = paths.map(path => 
        loadSpritesheet(path).then(() => {{
            loaded++;
            loadProgress.textContent = `${{loaded}}/${{paths.length}}`;
        }})
    );
    
    await Promise.all(promises);
}}




fetch('data.json')
    .then(r => r.json())
    .then(async d => {{
        dataTree = d.tree;
        spriteConfig = d.sprite_config;
        
        const loader = document.createElement('div');
        loader.id = 'loader';
        loader.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:black;color:white;display:flex;align-items:center;justify-content:center;z-index:9999;font-family:monospace;font-size:14px;';
        loader.innerHTML = '<div style="text-align:center;"><div id="load-text">loading spritesheets...</div><div id="load-progress">0/0</div></div>';
        document.body.appendChild(loader);
        
        const paths = getAllSpritesheetPaths(dataTree);
        document.getElementById('load-progress').textContent = `0/${{paths.length}}`;
        await preloadSpritesheets(paths);
        
        loader.remove();
        buildTree(dataTree, document.getElementById('tree'));
    }});





function buildTree(node, container, depth = 0, isLast = true, prefix = '') {{
    const connector = isLast ? '└── ' : '├── ';
    const item = document.createElement('div');
    item.className = 'tree-item';
    item.innerHTML = prefix + connector;
    const link = document.createElement('span');
    link.className = 'tree-link';
    link.textContent = node.name;
    link.dataset.path = node.path;
    link.onclick = (e) => {{
        e.stopPropagation();
        renderContent(node);
        updateTreeColors();
    }};
    item.appendChild(link);
    container.appendChild(item);
    const newPrefix = prefix + (isLast ? '    ' : '│   ');
    node.children.forEach((child, i) => {{
        buildTree(child, container, depth + 1, i === node.children.length - 1, newPrefix);
    }});
}}

function getDepthColor(depth) {{
    const colors = ['#4f4', '#5e5', '#6d6', '#7c7', '#8b8', '#9a9', '#a9a', '#b8b', '#c7c', '#d6d'];
    return colors[Math.min(depth, 9)];
}}

function updateTreeColors() {{
    if (!currentNode) return;
    document.querySelectorAll('.tree-link').forEach(link => link.style.color = '#4af');
    const currentLink = document.querySelector(`.tree-link[data-path="${{currentNode.path}}"]`);
    if (currentLink) currentLink.style.color = '#44f';
    
    const pathParts = currentNode.path.split('/');
    for (let i = 1; i < pathParts.length; i++) {{
        const ancestorPath = pathParts.slice(0, i).join('/');
        const ancestorLink = document.querySelector(`.tree-link[data-path="${{ancestorPath}}"]`);
        if (ancestorLink) ancestorLink.style.color = '#f44';
    }}

    function colorDescendants(node, depth = 0) {{
        node.children.forEach(child => {{
            const childLink = document.querySelector(`.tree-link[data-path="${{child.path}}"]`);
            if (childLink) childLink.style.color = getDepthColor(depth);
            colorDescendants(child, depth + 1);
        }});
    }}
    colorDescendants(currentNode, 0);
}}

function disposeScene(sceneData) {{
    if (sceneData.animationId) cancelAnimationFrame(sceneData.animationId);
    if (sceneData.resizeHandler) window.removeEventListener('resize', sceneData.resizeHandler);
    if (sceneData.labelContainer && sceneData.labelContainer.parentNode) {{
        sceneData.labelContainer.parentNode.removeChild(sceneData.labelContainer);
    }}
    if (sceneData.countDiv && sceneData.countDiv.parentNode) {{
        sceneData.countDiv.parentNode.removeChild(sceneData.countDiv);
    }}
    if (sceneData.renderer) {{
        sceneData.renderer.forceContextLoss();
        sceneData.renderer.dispose();
        if (sceneData.renderer.domElement.parentNode) {{
            sceneData.renderer.domElement.parentNode.removeChild(sceneData.renderer.domElement);
        }}
    }}
    if (sceneData.scene) sceneData.scene.clear();
}}










async function loadSpritesheet(path) {{
    if (spritesheets[path]) return spritesheets[path];
    
    return new Promise((resolve) => {{
        const loader = new THREE.TextureLoader();
        loader.load(path, (texture) => {{
            texture.minFilter = THREE.NearestFilter;
            texture.magFilter = THREE.NearestFilter;
            spritesheets[path] = texture;
            resolve(texture);
        }});
    }});
}}








async function createThreeScene(container, images, node) {{
    const scene = new THREE.Scene();
    const grouped = {{}};

    const SPRITESHEET_SIZE = spriteConfig.spritesheet_size;
    const SPRITE_SIZE = spriteConfig.sprite_size;
    const SPRITE_PADDING = spriteConfig.sprite_padding;
    const SPRITES_PER_ROW = spriteConfig.sprites_per_row;
    const STACK_SPACING = spriteConfig.stack_spacing;
    const SEED = spriteConfig.seed;
    const ORDERED_GRID_LAYOUT = spriteConfig.ordered_grid_layout;
    const ROTATION_SPEED = spriteConfig.rotation_speed;

const QUICKLOAD_THRESHOLD = spriteConfig.quickload_threshold;
const useInstantLoad = images.length > QUICKLOAD_THRESHOLD;
const delay = useInstantLoad ? 0 : 1;


    images.forEach(imgData => {{
        const parts = imgData.path.split('/');
        const folder = parts.slice(0, -1).join('/') || 'root';
        if (!grouped[folder]) grouped[folder] = [];
        grouped[folder].push(imgData);
    }});
    
    const folders = Object.keys(grouped);
    folders.forEach(folder => {{
        grouped[folder].sort((a, b) => a.global_index - b.global_index);
    }});
    
    const sharedGeometry = new THREE.PlaneGeometry(1, 1);
    
    const spacing = 1.5;
    let cols, rows, offsetX, offsetZ;
    let gridGroups;
    
    if (node.grid_layout) {{
        const parts = node.grid_layout.split('x');
        cols = parseInt(parts[0]);
        rows = parseInt(parts[1]);
        offsetX = (cols - 1) * spacing / 2;
        offsetZ = (rows - 1) * spacing / 2;
    }} else {{
        gridGroups = [];
        const processedFolders = new Set();
        
	 
        function collectGridChildren(n) {{
            if (n.grid_layout && n.ai.length > 0) {{
                const childFolders = folders.filter(f => f.startsWith(n.path + '/') || f === n.path);
                const [gCols, gRows] = ORDERED_GRID_LAYOUT ? n.grid_layout.split('x').map(Number) : [1, 1];
                gridGroups.push({{
                    folders: childFolders,
                    cols: gCols,
                    rows: gRows,
                    path: n.path
                }});
                childFolders.forEach(f => processedFolders.add(f));
            }} else if (n.children.length > 0) {{
                n.children.forEach(child => collectGridChildren(child));
            }} else if (n.ai.length > 0) {{
                const childFolders = folders.filter(f => f.startsWith(n.path + '/') || f === n.path);
                gridGroups.push({{
                    folders: childFolders,
                    cols: 1,
                    rows: 1,
                    path: n.path
                }});
                childFolders.forEach(f => processedFolders.add(f));
            }}
        }}
        
        node.children.forEach(child => collectGridChildren(child));
        
        if (gridGroups.length > 0) {{
            const occupiedGrid = new Map();
            
            const isOccupied = (gx, gy, w, h) => {{
                for (let dy = 0; dy < h; dy++) {{
                    for (let dx = 0; dx < w; dx++) {{
                        if (occupiedGrid.has(`${{gx + dx}},${{gy + dy}}`)) return true;
                    }}
                }}
                return false;
            }};
            
            const occupy = (gx, gy, w, h) => {{
                for (let dy = 0; dy < h; dy++) {{
                    for (let dx = 0; dx < w; dx++) {{
                        occupiedGrid.set(`${{gx + dx}},${{gy + dy}}`, true);
                    }}
                }}
            }};
            
            const findSpiralPosition = (w, h) => {{
                if (occupiedGrid.size === 0) return {{ x: 0, y: 0 }};
                
                let radius = 1;
                while (radius < 100) {{
                    for (let dy = -radius; dy <= radius; dy++) {{
                        for (let dx = -radius; dx <= radius; dx++) {{
                            if (Math.abs(dx) === radius || Math.abs(dy) === radius) {{
                                if (!isOccupied(dx, dy, w, h)) {{
                                    return {{ x: dx, y: dy }};
                                }}
                            }}
                        }}
                    }}
                    radius++;
                }}
                return {{ x: 0, y: 0 }};
            }};
            
            gridGroups.forEach(group => {{
                const pos = findSpiralPosition(group.cols, group.rows);
                group.gridX = pos.x;
                group.gridY = pos.y;
                occupy(pos.x, pos.y, group.cols, group.rows);
            }});
            
            let minGridX = Infinity, maxGridX = -Infinity;
            let minGridZ = Infinity, maxGridZ = -Infinity;
            gridGroups.forEach(group => {{
                minGridX = Math.min(minGridX, group.gridX);
                maxGridX = Math.max(maxGridX, group.gridX + group.cols - 1);
                minGridZ = Math.min(minGridZ, group.gridY);
                maxGridZ = Math.max(maxGridZ, group.gridY + group.rows - 1);
            }});
            
            offsetX = ((maxGridX + minGridX) / 2) * spacing;
            offsetZ = ((maxGridZ + minGridZ) / 2) * spacing;
        }} else {{
            cols = Math.ceil(Math.sqrt(folders.length));
            rows = Math.ceil(folders.length / cols);
            offsetX = (cols - 1) * spacing / 2;
            offsetZ = (rows - 1) * spacing / 2;
        }}
    }}

    let minX = Infinity, maxX = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;
    
    if (node.grid_layout) {{
        folders.forEach((folder, stackIdx) => {{
            const row = Math.floor(stackIdx / cols);
            const col = stackIdx % cols;
            const xPos = col * spacing - offsetX;
            const zPos = row * spacing - offsetZ;
            minX = Math.min(minX, xPos);
            maxX = Math.max(maxX, xPos);
            minZ = Math.min(minZ, zPos);
            maxZ = Math.max(maxZ, zPos);
        }});
    }} else if (gridGroups && gridGroups.length > 0) {{
        gridGroups.forEach(group => {{
            group.folders.forEach((folder, localIdx) => {{
                const row = Math.floor(localIdx / group.cols);
                const col = localIdx % group.cols;
                const xPos = (group.gridX + col) * spacing - offsetX;
                const zPos = (group.gridY + row) * spacing - offsetZ;
                minX = Math.min(minX, xPos);
                maxX = Math.max(maxX, xPos);
                minZ = Math.min(minZ, zPos);
                maxZ = Math.max(maxZ, zPos);
            }});
        }});
    }} else {{
        folders.forEach((folder, stackIdx) => {{
            const row = Math.floor(stackIdx / cols);
            const col = stackIdx % cols;
            const xPos = col * spacing - offsetX;
            const zPos = row * spacing - offsetZ;
            minX = Math.min(minX, xPos);
            maxX = Math.max(maxX, xPos);
            minZ = Math.min(minZ, zPos);
            maxZ = Math.max(maxZ, zPos);
        }});
    }}

    const meshMaxSize = 1.5 * 1.5;
    const geomWidth = maxX - minX + meshMaxSize;
    const geomDepth = maxZ - minZ + meshMaxSize;
    const maxDim = Math.max(geomWidth, geomDepth);
    const margin = 15;
    const baseFrustumSize = maxDim + margin;

    
    const seed = images.map(img => img.global_index).reduce((a, b) => a + b, 0);
    const rand = seededRandom(seed * SEED);  //this is a bit weird for sure
    const randomZoom = rand < 0.33 ? 0.1 : rand < 0.66 ? 1 : 0.1;
    const frustumSize = baseFrustumSize * randomZoom;

    const aspectRatio = container.clientWidth / container.clientHeight;
    const camera = new THREE.OrthographicCamera(
        frustumSize * aspectRatio / -2,
        frustumSize * aspectRatio / 2,
        frustumSize / 2,
        frustumSize / -2,
        0.1,
        1000
    );
    
    const renderer = new THREE.WebGLRenderer({{ alpha: true, antialias: true }});
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setClearColor(0x000000);
    container.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);

    const navButtons = document.createElement('div');
    navButtons.style.position = 'absolute';
    navButtons.style.top = '5px';
    navButtons.style.right = '5px';
    navButtons.style.display = 'flex';
    navButtons.style.gap = '5px';
    navButtons.style.zIndex = '100';

    const createButton = (text) => {{
        const btn = document.createElement('button');
        btn.textContent = text;
        btn.style.color = '#fff';
        btn.style.border = 'none';
        btn.style.padding = '3px';
        btn.style.cursor = 'pointer';
        btn.style.borderRadius = '50%';
        return btn;
    }};

    const topBtn = createButton();
    const rightBtn = createButton();
    const bottomBtn = createButton();
    const leftBtn = createButton();
    navButtons.append(topBtn, rightBtn, bottomBtn, leftBtn);
    container.appendChild(navButtons);

    let maxStackHeight = 0;
    folders.forEach(folder => {{
        maxStackHeight = Math.max(maxStackHeight, grouped[folder].length * STACK_SPACING);
    }});
    const midHeight = maxStackHeight / 2;

    topBtn.onclick = () => {{
        camera.position.set(0.01, midHeight + 15, 0);
        controls.target.set(0, midHeight, 0);
        controls.update();
    }};

    rightBtn.onclick = () => {{
        camera.position.set(15, midHeight + 0.3, 0.0);
        controls.target.set(0, midHeight, 0);
        controls.update();
    }};

    bottomBtn.onclick = () => {{
        camera.position.set(0.01, midHeight - 15, 0);
        controls.target.set(0, midHeight, 0);
        controls.update();
    }};

    leftBtn.onclick = () => {{
        camera.position.set(-15, midHeight + 0.3, 0.0);
        controls.target.set(0, midHeight, 0);
        controls.update();
    }};

    camera.position.set(10, 10 + midHeight, 10);
    controls.target.set(0, midHeight, 0);

    const labelContainer = document.createElement('div');
    labelContainer.style.position = 'absolute';
    labelContainer.style.top = '0';
    labelContainer.style.left = '0';
    labelContainer.style.width = '100%';
    labelContainer.style.height = '100%';
    labelContainer.style.pointerEvents = 'none';
    container.appendChild(labelContainer);


    const toggleBtn = document.createElement('button');
    toggleBtn.textContent = '';
    toggleBtn.style.position = 'absolute';
    toggleBtn.style.bottom = '5px';
    toggleBtn.style.left = '5px';
    toggleBtn.style.background = '#44f';
    toggleBtn.style.border = 'none';
    toggleBtn.style.width = '8px';
    toggleBtn.style.height = '8px';
    toggleBtn.style.borderRadius = '50%';
    toggleBtn.style.cursor = 'pointer';
    toggleBtn.style.padding = '0';
    toggleBtn.style.zIndex = '100';
    let labelsVisible = true;
    toggleBtn.onclick = () => {{
        labelsVisible = !labelsVisible;
        labelContainer.style.display = labelsVisible ? 'block' : 'none';
        toggleBtn.style.background = labelsVisible ? '#44f' : '#f44';
    }};
    container.appendChild(toggleBtn);

    const countDiv = document.createElement('div');
    countDiv.style.position = 'absolute';
    countDiv.style.bottom = '5px';
    countDiv.style.right = '5px';
    countDiv.style.color = 'white';
    countDiv.style.fontFamily = 'monospace';
    countDiv.style.fontSize = '11px';
    container.appendChild(countDiv);

    let loadedStacks = 0;
    let loadedImages = 0;
    const totalStacks = folders.length;
    const totalImages = images.length;

    const updateCount = () => {{
        const downColor = currentNode && currentNode.children.length > 0 ? '#4f4' : '#44f';
        const gridInfo = node.grid_layout ? ` [${{node.grid_layout}}]` : '';
        countDiv.innerHTML = `<span style="cursor:pointer;padding:0 5px;user-select:none;color:#f44" id="nav-up">&#60;</span> zoom: ${{randomZoom.toFixed(2)}}${{gridInfo}} | ${{loadedStacks}}/${{totalStacks}} stacks | ${{loadedImages}}/${{totalImages}} images <span style="cursor:pointer;padding:0 5px;user-select:none;color:${{downColor}}" id="nav-down">&#62;</span>`;
    }};

    updateCount();

    countDiv.addEventListener('click', (e) => {{
        if (e.target.id === 'nav-up') {{
            if (currentNode && currentNode.path) {{
                const parentPath = currentNode.path.split('/').slice(0, -1).join('/');
                const parentNode = findNodeByPath(dataTree, parentPath) || dataTree;
                renderContent(parentNode);
            }}
        }} else if (e.target.id === 'nav-down') {{
            if (currentNode && currentNode.children.length > 0) {{
                renderContent(currentNode.children[0]);
            }}
        }}
    }});

    const stackLabels = [];


    (async () => {{
        if (node.grid_layout) {{
            for (let stackIdx = 0; stackIdx < folders.length; stackIdx++) {{
                const folderName = folders[stackIdx];
                const stackImages = grouped[folderName];
                const row = Math.floor(stackIdx / cols);
                const col = stackIdx % cols;
                const xPos = col * spacing - offsetX;
                const zPos = row * spacing - offsetZ;

                for (let i = 0; i < stackImages.length; i++) {{
                    const imgData = stackImages[i];
                    const texture = await loadSpritesheet(imgData.ss);
                    if (!materialCache[imgData.ss]) {{
                        materialCache[imgData.ss] = new THREE.MeshBasicMaterial({{
                            map: texture,
                            side: THREE.DoubleSide,
                            transparent: true,
                            opacity: 1
                        }});
                    }}
                    const aspect = imgData.w / imgData.h;
                    const height = 1.5;
                    const width = height * aspect;
                    const mesh = new THREE.Mesh(sharedGeometry, materialCache[imgData.ss]);
                    mesh.scale.set(width, height, 1);
                    mesh.position.x = xPos;
                    mesh.position.y = i * STACK_SPACING;
                    mesh.position.z = zPos;
                    mesh.rotation.x = Math.PI / 2;
                    mesh.rotation.y = Math.PI;
                    mesh.rotation.z = Math.PI;
                    if (imgData.anim) {{
                        mesh.userData = {{
                            imgData: imgData,
                            spritesheet: imgData.ss
                        }};
                        mesh.onBeforeRender = function() {{
                            const frame = Math.floor(Date.now() / 100) % this.userData.imgData.fc;
                            const idx = this.userData.imgData.si + frame;
                            const sprite_col = idx % SPRITES_PER_ROW;
                            const sprite_row = Math.floor(idx / SPRITES_PER_ROW);
                            const u_start = (sprite_col * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                            const u_end = u_start + SPRITE_SIZE / SPRITESHEET_SIZE;
                            const v_start = 1 - ((sprite_row + 1) * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                            const v_end = 1 - (sprite_row * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                            const uvs = this.geometry.attributes.uv;
                            uvs.setXY(0, u_start, v_end);
                            uvs.setXY(1, u_end, v_end);
                            uvs.setXY(2, u_start, v_start);
                            uvs.setXY(3, u_end, v_start);
                            uvs.needsUpdate = true;
                        }};
                        mesh.geometry = sharedGeometry.clone();
                    }} else {{
                        const idx = imgData.idx;
                        const sprite_col = idx % SPRITES_PER_ROW;
                        const sprite_row = Math.floor(idx / SPRITES_PER_ROW);
                        const u_start = (sprite_col * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                        const u_end = u_start + imgData.w / SPRITESHEET_SIZE;
                        const v_start = 1 - ((sprite_row + 1) * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                        const v_end = 1 - (sprite_row * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                        const uvKey = `${{u_start.toFixed(6)}},${{u_end.toFixed(6)}},${{v_start.toFixed(6)}},${{v_end.toFixed(6)}}`;
                        if (!geometryCache[uvKey]) {{
                            const geometry = sharedGeometry.clone();
                            const uvs = geometry.attributes.uv;
                            uvs.setXY(0, u_start, v_end);
                            uvs.setXY(1, u_end, v_end);
                            uvs.setXY(2, u_start, v_start);
                            uvs.setXY(3, u_end, v_start);
                            geometryCache[uvKey] = geometry;
                        }}
                        mesh.geometry = geometryCache[uvKey];
                    }}
                    scene.add(mesh);
                    loadedImages++;
                    updateCount();
                    if (delay > 0) await new Promise(resolve => setTimeout(resolve, delay));

                }}

                loadedStacks++;
                updateCount();
                const topY = (stackImages.length - 1) * STACK_SPACING;
                const worldPos = new THREE.Vector3(xPos, topY, zPos);
                const label = document.createElement('span');

                const currentPath = currentNode ? currentNode.path : '';
                const currentFolderName = currentPath ? currentPath.split('/').pop() : '';
                const relativePath = folderName.startsWith(currentPath) && currentPath 
                    ? folderName.slice(currentPath.length + 1) 
                    : folderName;
                const pathParts = relativePath.split('/').filter(p => p);

                const displayParts = currentPath ? ['..', currentFolderName, ...pathParts] : pathParts;

                label.innerHTML = displayParts.map((part, idx) => {{
                    let color = '#4af';
                    let partPath = '';
                    
                    if (part === '..') {{
                        partPath = currentPath.split('/').slice(0, -1).join('/');
                        color = '#f44';
                    }} else if (idx === 1 && currentPath) {{
                        partPath = currentPath;
                        color = '#44f';
                    }} else {{
                        partPath = currentPath ? currentPath + '/' + pathParts.slice(0, idx - 1).join('/') : pathParts.slice(0, idx).join('/');
                        const relativeDepth = idx - 2;
                        color = getDepthColor(relativeDepth);
                    }}
                    
                    const shouldHide = displayParts.length > 4 && idx > 2 && idx < displayParts.length - 1;
                    const displayText = shouldHide ? '.' : part;
                    
                    return `<span style="background:black;padding:2px 4px;cursor:pointer;margin-right:2px;color:${{color}};pointer-events:auto" data-path="${{partPath}}">${{displayText}}</span>`;
                }}).join('/') + `<span style="background:black;padding:2px 4px;font-size:9px;margin-left:2px;pointer-events:auto">${{stackImages.length}}</span>`;

                label.style.position = 'absolute';
                label.style.pointerEvents = 'auto';
                label.style.pointerEvents = 'none';
                label.addEventListener('wheel', (e) => {{
                    e.stopPropagation();
                    renderer.domElement.dispatchEvent(new WheelEvent('wheel', e));
                }}, {{ passive: false }});

                label.style.cursor = 'pointer';
                label.onclick = () => {{
                    const folderNode = findNodeByPath(dataTree, folderName);
                    if (folderNode) renderContent(folderNode);
                }};
                label.style.color = 'white';
                label.style.fontFamily = 'monospace';
                label.style.fontSize = '11px';
                labelContainer.appendChild(label);

                stackLabels.push({{ element: label, position: worldPos, xPos, zPos, folderName }});
                label.style.pointerEvents = 'auto';
                label.querySelectorAll('span[data-path]').forEach(span => {{
                    span.onclick = (e) => {{
                        e.stopPropagation();
                        const node = findNodeByPath(dataTree, span.dataset.path);
                        if (node) renderContent(node);
                    }};
                }});
            }}
        }} else if (gridGroups && gridGroups.length > 0) {{
            for (const group of gridGroups) {{
                for (let localIdx = 0; localIdx < group.folders.length; localIdx++) {{
                    const folderName = group.folders[localIdx];
                    const stackImages = grouped[folderName];
                    const row = Math.floor(localIdx / group.cols);
                    const col = localIdx % group.cols;
                    const xPos = (group.gridX + col) * spacing - offsetX;
                    const zPos = (group.gridY + row) * spacing - offsetZ;

                    for (let i = 0; i < stackImages.length; i++) {{
                        const imgData = stackImages[i];
                        const texture = await loadSpritesheet(imgData.ss);
                        if (!materialCache[imgData.ss]) {{
                            materialCache[imgData.ss] = new THREE.MeshBasicMaterial({{
                                map: texture,
                                side: THREE.DoubleSide,
                                transparent: true,
                                opacity: 1
                            }});
                        }}
                        const aspect = imgData.w / imgData.h;
                        const height = 1.5;
                        const width = height * aspect;
                        const mesh = new THREE.Mesh(sharedGeometry, materialCache[imgData.ss]);
                        mesh.scale.set(width, height, 1);
                        mesh.position.x = xPos;
                        mesh.position.y = i * STACK_SPACING;
                        mesh.position.z = zPos;
                        mesh.rotation.x = Math.PI / 2;
                        mesh.rotation.y = Math.PI;
                        mesh.rotation.z = Math.PI;
                        if (imgData.anim) {{
                            mesh.userData = {{
                                imgData: imgData,
                                spritesheet: imgData.ss
                            }};
                            mesh.onBeforeRender = function() {{
                                const frame = Math.floor(Date.now() / 100) % this.userData.imgData.fc;
                                const idx = this.userData.imgData.si + frame;
                                const sprite_col = idx % SPRITES_PER_ROW;
                                const sprite_row = Math.floor(idx / SPRITES_PER_ROW);
                                const u_start = (sprite_col * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                                const u_end = u_start + SPRITE_SIZE / SPRITESHEET_SIZE;
                                const v_start = 1 - ((sprite_row + 1) * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                                const v_end = 1 - (sprite_row * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                                const uvs = this.geometry.attributes.uv;
                                uvs.setXY(0, u_start, v_end);
                                uvs.setXY(1, u_end, v_end);
                                uvs.setXY(2, u_start, v_start);
                                uvs.setXY(3, u_end, v_start);
                                uvs.needsUpdate = true;
                            }};
                            mesh.geometry = sharedGeometry.clone();
                        }} else {{
                            const idx = imgData.idx;
                            const sprite_col = idx % SPRITES_PER_ROW;
                            const sprite_row = Math.floor(idx / SPRITES_PER_ROW);
                            const u_start = (sprite_col * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                            const u_end = u_start + imgData.w / SPRITESHEET_SIZE;
                            const v_start = 1 - ((sprite_row + 1) * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                            const v_end = 1 - (sprite_row * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                            const uvKey = `${{u_start.toFixed(6)}},${{u_end.toFixed(6)}},${{v_start.toFixed(6)}},${{v_end.toFixed(6)}}`;
                            if (!geometryCache[uvKey]) {{
                                const geometry = sharedGeometry.clone();
                                const uvs = geometry.attributes.uv;
                                uvs.setXY(0, u_start, v_end);
                                uvs.setXY(1, u_end, v_end);
                                uvs.setXY(2, u_start, v_start);
                                uvs.setXY(3, u_end, v_start);
                                geometryCache[uvKey] = geometry;
                            }}
                            mesh.geometry = geometryCache[uvKey];
                        }}
                        scene.add(mesh);
                        loadedImages++;
                        updateCount();
                        if (delay > 0) await new Promise(resolve => setTimeout(resolve, delay));

                    }}

                    loadedStacks++;
                    updateCount();
                    const topY = (stackImages.length - 1) * STACK_SPACING;
                    const worldPos = new THREE.Vector3(xPos, topY, zPos);
                    const label = document.createElement('span');

                    const currentPath = currentNode ? currentNode.path : '';
                    const currentFolderName = currentPath ? currentPath.split('/').pop() : '';
                    const relativePath = folderName.startsWith(currentPath) && currentPath 
                        ? folderName.slice(currentPath.length + 1) 
                        : folderName;
                    const pathParts = relativePath.split('/').filter(p => p);

                    const displayParts = currentPath ? ['..', currentFolderName, ...pathParts] : pathParts;

                    label.innerHTML = displayParts.map((part, idx) => {{
                        let color = '#4af';
                        let partPath = '';
                        
                        if (part === '..') {{
                            partPath = currentPath.split('/').slice(0, -1).join('/');
                            color = '#f44';
                        }} else if (idx === 1 && currentPath) {{
                            partPath = currentPath;
                            color = '#44f';
                        }} else {{
                            partPath = currentPath ? currentPath + '/' + pathParts.slice(0, idx - 1).join('/') : pathParts.slice(0, idx).join('/');
                            const relativeDepth = idx - 2;
                            color = getDepthColor(relativeDepth);
                        }}
                        
                        const shouldHide = displayParts.length > 4 && idx > 2 && idx < displayParts.length - 1;
                        const displayText = shouldHide ? '.' : part;
                        
                        return `<span style="background:black;padding:2px 4px;cursor:pointer;margin-right:2px;color:${{color}};pointer-events:auto" data-path="${{partPath}}">${{displayText}}</span>`;
                    }}).join('/') + `<span style="background:black;padding:2px 4px;font-size:9px;margin-left:2px;pointer-events:auto">${{stackImages.length}}</span>`;

                    label.style.position = 'absolute';
                    label.style.pointerEvents = 'auto';
                    label.style.pointerEvents = 'none';
                    label.addEventListener('wheel', (e) => {{
                        e.stopPropagation();
                        renderer.domElement.dispatchEvent(new WheelEvent('wheel', e));
                    }}, {{ passive: false }});

                    label.style.cursor = 'pointer';
                    label.onclick = () => {{
                        const folderNode = findNodeByPath(dataTree, folderName);
                        if (folderNode) renderContent(folderNode);
                    }};
                    label.style.color = 'white';
                    label.style.fontFamily = 'monospace';
                    label.style.fontSize = '11px';
                    labelContainer.appendChild(label);

                    stackLabels.push({{ element: label, position: worldPos, xPos, zPos, folderName }});
                    label.style.pointerEvents = 'auto';
                    label.querySelectorAll('span[data-path]').forEach(span => {{
                        span.onclick = (e) => {{
                            e.stopPropagation();
                            const node = findNodeByPath(dataTree, span.dataset.path);
                            if (node) renderContent(node);
                        }};
                    }});
                }}
            }}
        }} else {{
            for (let stackIdx = 0; stackIdx < folders.length; stackIdx++) {{
                const folderName = folders[stackIdx];
                const stackImages = grouped[folderName];
                const row = Math.floor(stackIdx / cols);
                const col = stackIdx % cols;
                const xPos = col * spacing - offsetX;
                const zPos = row * spacing - offsetZ;

                for (let i = 0; i < stackImages.length; i++) {{
                    const imgData = stackImages[i];
                    const texture = await loadSpritesheet(imgData.ss);
                    if (!materialCache[imgData.ss]) {{
                        materialCache[imgData.ss] = new THREE.MeshBasicMaterial({{
                            map: texture,
                            side: THREE.DoubleSide,
                            transparent: true,
                            opacity: 1
                        }});
                    }}
                    const aspect = imgData.w / imgData.h;
                    const height = 1.5;
                    const width = height * aspect;
                    const mesh = new THREE.Mesh(sharedGeometry, materialCache[imgData.ss]);
                    mesh.scale.set(width, height, 1);
                    mesh.position.x = xPos;
                    mesh.position.y = i * STACK_SPACING;
                    mesh.position.z = zPos;
                    mesh.rotation.x = Math.PI / 2;
                    mesh.rotation.y = Math.PI;
                    mesh.rotation.z = Math.PI;
                    if (imgData.anim) {{
                        mesh.userData = {{
                            imgData: imgData,
                            spritesheet: imgData.ss
                        }};
                        mesh.onBeforeRender = function() {{
                            const frame = Math.floor(Date.now() / 100) % this.userData.imgData.fc;
                            const idx = this.userData.imgData.si + frame;
                            const sprite_col = idx % SPRITES_PER_ROW;
                            const sprite_row = Math.floor(idx / SPRITES_PER_ROW);
                            const u_start = (sprite_col * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                            const u_end = u_start + SPRITE_SIZE / SPRITESHEET_SIZE;
                            const v_start = 1 - ((sprite_row + 1) * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                            const v_end = 1 - (sprite_row * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                            const uvs = this.geometry.attributes.uv;
                            uvs.setXY(0, u_start, v_end);
                            uvs.setXY(1, u_end, v_end);
                            uvs.setXY(2, u_start, v_start);
                            uvs.setXY(3, u_end, v_start);
                            uvs.needsUpdate = true;
                        }};
                        mesh.geometry = sharedGeometry.clone();
                    }} else {{
                        const idx = imgData.idx;
                        const sprite_col = idx % SPRITES_PER_ROW;
                        const sprite_row = Math.floor(idx / SPRITES_PER_ROW);
                        const u_start = (sprite_col * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                        const u_end = u_start + imgData.w / SPRITESHEET_SIZE;
                        const v_start = 1 - ((sprite_row + 1) * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                        const v_end = 1 - (sprite_row * SPRITE_SIZE + SPRITE_PADDING) / SPRITESHEET_SIZE;
                        const uvKey = `${{u_start.toFixed(6)}},${{u_end.toFixed(6)}},${{v_start.toFixed(6)}},${{v_end.toFixed(6)}}`;
                        if (!geometryCache[uvKey]) {{
                            const geometry = sharedGeometry.clone();
                            const uvs = geometry.attributes.uv;
                            uvs.setXY(0, u_start, v_end);
                            uvs.setXY(1, u_end, v_end);
                            uvs.setXY(2, u_start, v_start);
                            uvs.setXY(3, u_end, v_start);
                            geometryCache[uvKey] = geometry;
                        }}
                        mesh.geometry = geometryCache[uvKey];
                    }}
                    scene.add(mesh);
                    loadedImages++;
                    updateCount();
                    if (delay > 0) await new Promise(resolve => setTimeout(resolve, delay));

                }}

                loadedStacks++;
                updateCount();
                const topY = (stackImages.length - 1) * STACK_SPACING;
                const worldPos = new THREE.Vector3(xPos, topY, zPos);
                const label = document.createElement('span');

                const currentPath = currentNode ? currentNode.path : '';
                const currentFolderName = currentPath ? currentPath.split('/').pop() : '';
                const relativePath = folderName.startsWith(currentPath) && currentPath 
                    ? folderName.slice(currentPath.length + 1) 
                    : folderName;
                const pathParts = relativePath.split('/').filter(p => p);

                const displayParts = currentPath ? ['..', currentFolderName, ...pathParts] : pathParts;

                label.innerHTML = displayParts.map((part, idx) => {{
                    let color = '#4af';
                    let partPath = '';
                    
                    if (part === '..') {{
                        partPath = currentPath.split('/').slice(0, -1).join('/');
                        color = '#f44';
                    }} else if (idx === 1 && currentPath) {{
                        partPath = currentPath;
                        color = '#44f';
                    }} else {{
                        partPath = currentPath ? currentPath + '/' + pathParts.slice(0, idx - 1).join('/') : pathParts.slice(0, idx).join('/');
                        const relativeDepth = idx - 2;
                        color = getDepthColor(relativeDepth);
                    }}
                    
                    const shouldHide = displayParts.length > 4 && idx > 2 && idx < displayParts.length - 1;
                    const displayText = shouldHide ? '.' : part;
                    
                    return `<span style="background:black;padding:2px 4px;cursor:pointer;margin-right:2px;color:${{color}};pointer-events:auto" data-path="${{partPath}}">${{displayText}}</span>`;
                }}).join('/') + `<span style="background:black;padding:2px 4px;font-size:9px;margin-left:2px;pointer-events:auto">${{stackImages.length}}</span>`;

                label.style.position = 'absolute';
                label.style.pointerEvents = 'auto';
                label.style.pointerEvents = 'none';
                label.addEventListener('wheel', (e) => {{
                    e.stopPropagation();
                    renderer.domElement.dispatchEvent(new WheelEvent('wheel', e));
                }}, {{ passive: false }});

                label.style.cursor = 'pointer';
                label.onclick = () => {{
                    const folderNode = findNodeByPath(dataTree, folderName);
                    if (folderNode) renderContent(folderNode);
                }};
                label.style.color = 'white';
                label.style.fontFamily = 'monospace';
                label.style.fontSize = '11px';
                labelContainer.appendChild(label);

                stackLabels.push({{ element: label, position: worldPos, xPos, zPos, folderName }});
                label.style.pointerEvents = 'auto';
                label.querySelectorAll('span[data-path]').forEach(span => {{
                    span.onclick = (e) => {{
                        e.stopPropagation();
                        const node = findNodeByPath(dataTree, span.dataset.path);
                        if (node) renderContent(node);
                    }};
                }});
            }}
        }}
    }})();

    const stats = new Stats();
    stats.showPanel(0);
    container.appendChild(stats.dom);
    stats.dom.style.position = 'absolute';
    stats.dom.style.top = '30px';
    stats.dom.style.left = '5px';

    const resizeHandler = () => {{
        const newAspect = container.clientWidth / container.clientHeight;
        camera.left = frustumSize * newAspect / -2;
        camera.right = frustumSize * newAspect / 2;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    }};

    const sceneData = {{ scene, renderer, camera, controls, animationId: null, resizeHandler, stats, labelContainer, countDiv }};

    let frameCount = 0;
    function animate() {{
        stats.begin();
        sceneData.animationId = requestAnimationFrame(animate);
        controls.update();
        const rotationAngle = Date.now() * ROTATION_SPEED;
        scene.rotation.y = rotationAngle;
        
        if (frameCount % 10 === 0) {{
            const raycaster = new THREE.Raycaster();
            raycaster.camera = camera;
            stackLabels.forEach(({{ element, position, xPos, zPos }}, idx) => {{
                const rotatedX = xPos * Math.cos(rotationAngle) + zPos * Math.sin(rotationAngle);
                const rotatedZ = -xPos * Math.sin(rotationAngle) + zPos * Math.cos(rotationAngle);
                const rotatedPos = new THREE.Vector3(rotatedX, position.y + 0.01, rotatedZ);
                
                const direction = new THREE.Vector3().subVectors(camera.position, rotatedPos).normalize();
                raycaster.set(rotatedPos, direction);
                const meshes = scene.children.filter(c => c.type === 'Mesh');
                const intersects = raycaster.intersectObjects(meshes, false);
                
                element.style.display = intersects.length > 0 ? 'none' : 'block';
            }});
        }}
        frameCount++;

        stackLabels.forEach(({{ element, position, xPos, zPos }}) => {{
            const rotatedX = xPos * Math.cos(rotationAngle) + zPos * Math.sin(rotationAngle);
            const rotatedZ = -xPos * Math.sin(rotationAngle) + zPos * Math.cos(rotationAngle);
            const rotatedPos = new THREE.Vector3(rotatedX, position.y, rotatedZ);
            const screenPos = rotatedPos.project(camera);
            const x = (screenPos.x * 0.5 + 0.5) * container.clientWidth;
            const y = (-(screenPos.y * 0.5) + 0.5) * container.clientHeight;
            element.style.left = x + 'px';
            element.style.top = y + 'px';
        }});
        renderer.render(scene, camera);
        stats.end();
    }}
    animate();

    activeScenes.push(sceneData);
    window.addEventListener('resize', resizeHandler);
}}

async function loadText(path) {{
    const res = await fetch(path);
    return await res.text();
}}

function findNodeByPath(node, targetPath) {{
    if (node.path === targetPath || node.name === targetPath) return node;
    for (const child of node.children) {{
        const found = findNodeByPath(child, targetPath);
        if (found) return found;
    }}
    return null;
}}

let currentNode = null;

async function renderContent(node) {{

    const RANDOM_TEXTDIV_POSITION = spriteConfig.random_textdiv_position;
    const SEED = spriteConfig.seed;

    currentNode = node;
    updateTreeColors();

    activeScenes.forEach(disposeScene);
    activeScenes = [];
    const contentDiv = document.getElementById('content');
    contentDiv.innerHTML = '';
    
    console.log('=== renderContent DEBUG ===');
    console.log('node:', node);
    console.log('node.children.length:', node.children.length);
    console.log('node.ai.length:', node.ai.length);
    console.log('node.at.length:', node.at.length);
    console.log('node.sa (stop_accum):', node.sa);
    
    let children = node.children.length > 0 ? node.children : [node];
    console.log('children before filter:', children.map(c => ({{ name: c.name, ai: c.ai.length, at: c.at.length, sa: c.sa }})));
    
    children = children.map(child => {{
        if (child.sa || node.sa) {{
            return {{ ...child, at: [] }};
        }}
        return child;
    }});
    
    children = children.filter(child => child.ai.length > 0 || child.at.length > 0);
    console.log('children after filter:', children.map(c => ({{ name: c.name, ai: c.ai.length, at: c.at.length }})));
    
    const count = children.length;
    console.log('final count:', count);
    const cols = Math.ceil(Math.sqrt(count));
    
    for (const child of children) {{
        console.log('creating div for:', child.name, 'ai:', child.ai.length, 'at:', child.at.length);
        console.log('creating div for:', child.name, 'ai:', child.ai.length, 'at:', child.at.length);
        const div = document.createElement('div');
        div.className = 'content-div';
        div.style.width = `calc(${{100/cols}}% - 2px)`;
        div.style.height = count <= 2 ? '100%' : `calc(${{100/Math.ceil(count/cols)}}% - 2px)`;

        const label = document.createElement('div');
        label.className = 'div-label';
        const pathParts = child.path.split('/');
        label.innerHTML = pathParts.map((part, idx) => {{
            const partPath = pathParts.slice(0, idx + 1).join('/');
            let color = '#4af';
            if (currentNode) {{
                if (partPath === currentNode.path) color = '#44f';
                else if (currentNode.path.startsWith(partPath + '/')) color = '#f44';
                else if (currentNode.children.some(c => c.path === partPath)) color = '#4f4';
            }}
            return `<span style="color:${{color}};cursor:pointer" data-path="${{partPath}}">${{part}}</span>`;
        }}).join('/');
        label.style.pointerEvents = 'auto';
        label.querySelectorAll('span[data-path]').forEach(span => {{
            span.onclick = (e) => {{
                e.stopPropagation();
                const node = findNodeByPath(dataTree, span.dataset.path);
                if (node) renderContent(node);
            }};
        }});

        div.appendChild(label);


        if (child.ai.length > 0 && child.at.length > 0) {{
            div.style.display = 'flex';
            div.style.flexDirection = 'row';
            const textDiv = document.createElement('div');
            textDiv.className = 'text-content';
            textDiv.style.flex = '1';
            textDiv.style.border = '1px solid white';
            textDiv.style.position = 'relative';
            textDiv.style.overflow = 'auto';
            let htmlContent = '';
            for (const path of child.at) {{
                htmlContent += await loadText(path);
            }}
            
            const hasParent = currentNode.path.split('/').length > 1;
            const firstChildWithText = currentNode.children?.find(c => c.at.length > 0);
            const leftColor = hasParent ? '#f44' : '#44f';
            const rightColor = firstChildWithText ? '#4f4' : '#44f';
            
            textDiv.innerHTML = htmlContent + `<div style="position:absolute;bottom:5px;right:5px;color:white;font-family:monospace;font-size:11px;background:black;padding:2px 5px;border:1px solid white;z-index:100"><span style="cursor:pointer;padding:0 5px;user-select:none;color:${{leftColor}}" class="text-nav-left">&#60;</span><span style="padding:0 2px">texts</span><span style="cursor:pointer;padding:0 5px;user-select:none;color:${{rightColor}}" class="text-nav-right">&#62;</span></div>`;

            const navLeft = textDiv.querySelector('.text-nav-left');
            const navRight = textDiv.querySelector('.text-nav-right');
            
            navLeft.onclick = () => {{
                if (currentNode && currentNode.path) {{
                    const parentPath = currentNode.path.split('/').slice(0, -1).join('/');
                    const parentNode = findNodeByPath(dataTree, parentPath) || dataTree;
                    if (parentNode && parentNode.at.length > 0) {{
                        renderContent(parentNode);
                    }}
                }}
            }};
            
            navRight.onclick = () => {{
                if (currentNode && currentNode.children && currentNode.children.length > 0) {{
                    const firstChildWithText = currentNode.children.find(c => c.at.length > 0);
                    if (firstChildWithText) {{
                        renderContent(firstChildWithText);
                    }}
                }}
            }};
            
            //div.appendChild(textDiv);
            const imgDiv = document.createElement('div');
            imgDiv.style.flex = '1';
            imgDiv.style.position = 'relative';
            imgDiv.style.border = '1px solid white';
            imgDiv.style.overflow = 'hidden';
            //div.appendChild(imgDiv);

           if (RANDOM_TEXTDIV_POSITION) {{
               const seed = child.path.split('').reduce((a, c) => a + c.charCodeAt(0), 0) * SEED;
               const rand = seededRandom(seed);
               if (rand < 0.5) {{
                   div.appendChild(textDiv);
                   div.appendChild(imgDiv);
               }} else {{
                   div.appendChild(imgDiv);
                   div.appendChild(textDiv);
               }}
           }} else {{
               div.appendChild(textDiv);
               div.appendChild(imgDiv);
           }} 

            setTimeout(() => createThreeScene(imgDiv, child.ai, child), 0);

        }} else if (child.ai.length > 0) {{
            setTimeout(() => createThreeScene(div, child.ai, child), 0);

        }} else if (child.at.length > 0) {{
            div.className = 'content-div text-content';
            div.style.position = 'relative';
            let htmlContent = '';
            for (const path of child.at) {{
                htmlContent += await loadText(path);
            }}
            
            const pathParts = child.path.split('/');
            const labelHtml = pathParts.map((part, idx) => {{
                const partPath = pathParts.slice(0, idx + 1).join('/');
                let color = '#4af';
                if (currentNode) {{
                    if (partPath === currentNode.path) color = '#44f';
                    else if (currentNode.path.startsWith(partPath + '/')) color = '#f44';
                    else if (currentNode.children.some(c => c.path === partPath)) color = '#4f4';
                }}
                return `<span style="color:${{color}};cursor:pointer" data-path="${{partPath}}">${{part}}</span>`;
            }}).join('/');
            
            const navHtml = `<div style="position:absolute;bottom:5px;right:5px;color:white;font-family:monospace;font-size:11px;background:black;padding:2px 5px;border:1px solid white"><span style="cursor:pointer;padding:0 5px;user-select:none;color:#4af" class="text-nav-left">&#60;</span><span style="padding:0 2px">texts</span><span style="cursor:pointer;padding:0 5px;user-select:none;color:#4af" class="text-nav-right">&#62;</span></div>`;
            
            div.innerHTML = htmlContent + '<style>.div-label {{ position: absolute; top: 5px; left: 5px; background: black; padding: 2px 5px; border: 1px solid white; z-index: 100; pointer-events: auto; }}</style><div class="div-label">' + labelHtml + '</div>' + navHtml;
            
            const textLabel = div.querySelector('.div-label');
            textLabel.querySelectorAll('span[data-path]').forEach(span => {{
                span.onclick = (e) => {{
                    e.stopPropagation();
                    const node = findNodeByPath(dataTree, span.dataset.path);
                    if (node) renderContent(node);
                }};
            }});
            
            const navLeft = div.querySelector('.text-nav-left');
            const navRight = div.querySelector('.text-nav-right');
            
            navLeft.onclick = () => {{
                if (currentNode && currentNode.path) {{
                    const parentPath = currentNode.path.split('/').slice(0, -1).join('/');
                    const parentNode = findNodeByPath(dataTree, parentPath) || dataTree;
                    if (parentNode && parentNode.at.length > 0) {{
                        renderContent(parentNode);
                    }}
                }}
            }};
            
            navRight.onclick = () => {{
                if (currentNode && currentNode.children && currentNode.children.length > 0) {{
                    const firstChildWithText = currentNode.children.find(c => c.at.length > 0);
                    if (firstChildWithText) {{
                        renderContent(firstChildWithText);
                    }}
                }}
            }};
        }}

        contentDiv.appendChild(div);
    }}
}}
</script>
</body>
</html>''')

print("Generated spritesheets, data.json and index.html")
