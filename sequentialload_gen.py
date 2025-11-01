from pathlib import Path
import json
from PIL import Image
from natsort import natsorted

def resize_image(img):
    w, h = img.size
    longest = max(w, h)
    if longest != 256:
        scale = 256 / longest
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
    return img

def scan_folder(path, ignore=['venv', '__pycache__', '.git', 'spritesheets']):
    if path.name in ignore:
        return None
    
    images = []
    texts = []
    children = []
    
    if path.is_dir():
        for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
            if item.name in ignore:
                continue
            if item.is_file():
                if item.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                    images.append(str(item.relative_to('.')))
                elif item.suffix.lower() in ['.txt', '.md']:
                    texts.append(str(item.relative_to('.')))
            elif item.is_dir():
                child = scan_folder(item, ignore)
                if child:
                    children.append(child)
        
        all_images = images.copy()
        all_texts = texts.copy()
        for child in children:
            all_images.extend(child['all_images'])
            all_texts.extend(child['all_texts'])
    
    content_type = 'empty'
    if all_images and all_texts:
        content_type = 'mixed'
    elif all_images:
        content_type = 'images'
    elif all_texts:
        content_type = 'text'
    
    return {
        'name': path.name,
        'path': str(path.relative_to('.')),
        'type': content_type,
        'children': children,
        'all_images': all_images,
        'all_texts': all_texts,
        'own_images': images,
        'own_texts': texts
    }

root = scan_folder(Path('.'))

all_image_paths = []
def collect_images(node):
    all_image_paths.extend(node['own_images'])
    for child in node['children']:
        collect_images(child)
collect_images(root)

all_image_paths = natsorted(all_image_paths)


Path('spritesheets').mkdir(exist_ok=True)

sprite_data = {}
sheet_idx = 0
slot_idx = 0
sheet = Image.new('RGBA', (2048, 2048), (0, 0, 0, 0))








for idx, img_path in enumerate(all_image_paths):
    img = Image.open(img_path).convert('RGBA')
    img = resize_image(img)
    
    col = slot_idx % 8
    row = slot_idx // 8
    x = col * 256 + 1
    y = row * 256 + 1
    
    sheet.paste(img, (x, y))
    
    sprite_data[img_path] = {
        'spritesheet': f'spritesheets/sprites_{sheet_idx}.png',
        'index': slot_idx,
        'global_index': idx,
        'width': img.width,
        'height': img.height,
        'original_path': img_path
    }
    
    slot_idx += 1
    if slot_idx >= 64:
        sheet.save(f'spritesheets/sprites_{sheet_idx}.png')
        sheet_idx += 1
        slot_idx = 0
        sheet = Image.new('RGBA', (2048, 2048), (0, 0, 0, 0))





if slot_idx > 0:
    sheet.save(f'spritesheets/sprites_{sheet_idx}.png')

def replace_images(node):
    node['all_images'] = [sprite_data[p] for p in node['all_images']]
    node['own_images'] = [sprite_data[p] for p in node['own_images']]
    for child in node['children']:
        replace_images(child)

replace_images(root)

with open('data.json', 'w') as f:
    json.dump(root, f, indent=2)

with open('index.html', 'w') as f:
    f.write('''<!DOCTYPE html>
<html>
<head>
<script src="https://unpkg.com/stats.js@0.17.0/build/stats.min.js"></script>

<meta charset="utf-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
    background: black; 
    color: white; 
    font-family: monospace; 
    font-size: 11px;
    display: flex;
    height: 100vh;
    overflow: hidden;
}
#tree { 
    width: 300px; 
    border-right: 1px solid white; 
    overflow-y: auto; 
    padding: 10px;
}
#content { 
    flex: 1; 
    display: flex;
    flex-wrap: wrap;
    overflow: hidden;
}
.tree-item { white-space: pre; }
.tree-link { cursor: pointer; color: #4af; }
.tree-link:hover { background: #222; }
.content-div {
    border: 1px solid white;
    position: relative;
    overflow: hidden;
}
.div-label {
    position: absolute;
    top: 5px;
    left: 5px;
    background: black;
    padding: 2px 5px;
    border: 1px solid white;
    z-index: 100;
}
.text-content {
    padding: 20px;
    overflow-y: auto;
    white-space: pre-wrap;
}
canvas { display: block; width: 100%; height: 100%; }
</style>
</head>
<body>
<div id="tree"></div>
<div id="content"></div>
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/jsm/"
  }
}
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

let data;
let activeScenes = [];
const spritesheets = {};
const pendingLoads = {};
const materialCache = {};
const geometryCache = {};


fetch('data.json')
    .then(r => r.json())
    .then(d => {
        data = d;
        buildTree(data, document.getElementById('tree'));
    });

function buildTree(node, container, depth = 0, isLast = true, prefix = '') {
    const connector = isLast ? '└── ' : '├── ';
    
    const item = document.createElement('div');
    item.className = 'tree-item';
    item.innerHTML = prefix + connector;
    
    const link = document.createElement('span');
    link.className = 'tree-link';
    link.textContent = node.name;
    link.onclick = (e) => {
        e.stopPropagation();
        renderContent(node);
    };
    
    item.appendChild(link);
    container.appendChild(item);
    
    const newPrefix = prefix + (isLast ? '    ' : '│   ');
    node.children.forEach((child, i) => {
        buildTree(child, container, depth + 1, i === node.children.length - 1, newPrefix);
    });
}




function disposeScene(sceneData) {
    if (sceneData.animationId) cancelAnimationFrame(sceneData.animationId);
    if (sceneData.resizeHandler) {
        window.removeEventListener('resize', sceneData.resizeHandler);
    }
    if (sceneData.renderer) {
        sceneData.renderer.forceContextLoss();
        sceneData.renderer.dispose();
        if (sceneData.renderer.domElement.parentNode) {
            sceneData.renderer.domElement.parentNode.removeChild(sceneData.renderer.domElement);
        }
    }
    if (sceneData.scene) {
        sceneData.scene.clear();

    }

    if (sceneData.controls) {
        const elem = sceneData.controls.domElement;
        elem.removeEventListener('mousedown', sceneData.controls.onMouseDown);
        elem.removeEventListener('mousemove', sceneData.controls.onMouseMove);
        elem.removeEventListener('mouseup', sceneData.controls.onMouseUp);
        elem.removeEventListener('wheel', sceneData.controls.onWheel);
}
    console.log('cache - geom:', Object.keys(geometryCache).length, 'mat:', Object.keys(materialCache).length, 'tex:', Object.keys(spritesheets).length);
}



async function loadSpritesheet(path) {
    if (spritesheets[path]) {
        return spritesheets[path];
    }
    
    if (pendingLoads[path]) {
        return pendingLoads[path];
    }
    
    pendingLoads[path] = new Promise((resolve) => {
        const loader = new THREE.TextureLoader();
        loader.load(path, (texture) => {
            texture.minFilter = THREE.NearestFilter;
            texture.magFilter = THREE.NearestFilter;
            spritesheets[path] = texture;
            delete pendingLoads[path];
            resolve(texture);
        });
    });
    
    return pendingLoads[path];
}    
    
    
    async function createThreeScene(container, images) {
        const scene = new THREE.Scene();
        const usedSpritesheets = new Set();

        const frustumSize = 10;
        const aspectRatio = container.clientWidth / container.clientHeight;
        const camera = new THREE.OrthographicCamera(
            frustumSize * aspectRatio / -2,
            frustumSize * aspectRatio / 2,
            frustumSize / 2,
            frustumSize / -2,
            0.1,
            1000
        );

    camera.position.set(10, 10, 10);
    
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setClearColor(0x000000);
    container.appendChild(renderer.domElement);
    
    //const controls = new OrbitControls(camera, renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);

    const grouped = {};


    const gridHelper = new THREE.GridHelper(20, 20, 0x444444, 0x222222);
    gridHelper.rotation.y = Math.PI / 2;
    scene.add(gridHelper);
    
    const axesHelper = new THREE.AxesHelper(5);
    scene.add(axesHelper);

    images.forEach(imgData => {
        const parts = imgData.original_path.split('/');
        const folder = parts.length > 1 ? parts[parts.length - 2] : 'root';
        if (!grouped[folder]) grouped[folder] = [];
        grouped[folder].push(imgData);
    });
    
    const folders = Object.keys(grouped);
    folders.forEach(folder => {
        grouped[folder].sort((a, b) => a.global_index - b.global_index);
    });
    
    const sharedGeometry = new THREE.PlaneGeometry(1, 1);
  
 
    const cols = Math.ceil(Math.sqrt(folders.length));
    const spacing = 1.5;
    



    (async () => {
        for (let stackIdx = 0; stackIdx < folders.length; stackIdx++) {
            const folder = folders[stackIdx];
            const stackImages = grouped[folder];
            const row = Math.floor(stackIdx / cols);
            const col = stackIdx % cols;
            const xPos = (col - cols / 2) * spacing;
            const zPos = (row - Math.ceil(folders.length / cols) / 2) * spacing;
            
            for (let i = 0; i < stackImages.length; i++) {
                const imgData = stackImages[i];
                const texture = await loadSpritesheet(imgData.spritesheet);
    
                if (!materialCache[imgData.spritesheet]) {
                    materialCache[imgData.spritesheet] = new THREE.MeshBasicMaterial({
                        map: texture,
                        side: THREE.DoubleSide,
                        transparent: true,
                        opacity: 1
                    });
                }
                
                const idx = imgData.index;
                const sprite_col = idx % 8;
                const sprite_row = Math.floor(idx / 8);
                
                const u_start = (sprite_col * 256 + 1) / 2048;
                const u_end = u_start + imgData.width / 2048;
                const v_start = 1 - ((sprite_row + 1) * 256 + 1) / 2048;
                const v_end = 1 - (sprite_row * 256 + 1) / 2048;
                
                const uvKey = `${u_start.toFixed(6)},${u_end.toFixed(6)},${v_start.toFixed(6)},${v_end.toFixed(6)}`;
                if (!geometryCache[uvKey]) {
                    const geometry = sharedGeometry.clone();
                    const uvs = geometry.attributes.uv;
                    uvs.setXY(0, u_start, v_end);
                    uvs.setXY(1, u_end, v_end);
                    uvs.setXY(2, u_start, v_start);
                    uvs.setXY(3, u_end, v_start);
                    geometryCache[uvKey] = geometry;
                }
                const geometry = geometryCache[uvKey];
                
                const aspect = imgData.width / imgData.height;
                const height = 1.5;
                const width = height * aspect;
                
                const mesh = new THREE.Mesh(geometry, materialCache[imgData.spritesheet]);
                mesh.scale.set(width, height, 1);
                mesh.position.x = xPos;
                mesh.position.y = i * 0.1;
                mesh.position.z = zPos;
                mesh.rotation.x = Math.PI / 2;
                mesh.rotation.y = Math.PI;
                mesh.rotation.z = Math.PI;
                
                scene.add(mesh);
                await new Promise(resolve => setTimeout(resolve, 2));
            }
        }
    })();


 
    
    const stats = new Stats();
    stats.showPanel(0);
    container.appendChild(stats.dom);
    stats.dom.style.position = 'absolute';
    stats.dom.style.top = '30px';
    stats.dom.style.left = '5px';
   


    const resizeHandler = () => {
        const newAspect = container.clientWidth / container.clientHeight;
        camera.left = frustumSize * newAspect / -2;
        camera.right = frustumSize * newAspect / 2;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    };
    
    const sceneData = { scene, renderer, camera, controls, animationId: null, resizeHandler, stats };
    const rotationAxis = new THREE.Vector3(0, 1, 0);

 
    function animate() {
        stats.begin();
        sceneData.animationId = requestAnimationFrame(animate);
        controls.update();
        scene.rotateOnAxis(rotationAxis, 0.001);
        renderer.render(scene, camera);
        stats.end();
    }
    animate();
    
    activeScenes.push(sceneData);

    window.addEventListener('resize', resizeHandler);
    
    window.addEventListener('resize', () => {
        const newAspect = container.clientWidth / container.clientHeight;
        camera.left = frustumSize * newAspect / -2;
        camera.right = frustumSize * newAspect / 2;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });
}

async function loadText(path) {
    const res = await fetch(path);
    return await res.text();
}

async function renderContent(node) {
    console.log('scenes before:', activeScenes.length);

    activeScenes.forEach(disposeScene);
    activeScenes = [];
    console.log('scenes after:', activeScenes.length);
    
    const contentDiv = document.getElementById('content');
    contentDiv.innerHTML = '';
    
    
    const children = node.children.length > 0 ? node.children : [node];
    const count = children.length;

    const cols = Math.ceil(Math.sqrt(count));
    
    for (const child of children) {
        const div = document.createElement('div');
        div.className = 'content-div';
        div.style.width = `calc(${100/cols}% - 2px)`;
        div.style.height = count <= 2 ? '100%' : `calc(${100/Math.ceil(count/cols)}% - 2px)`;
        
        const label = document.createElement('div');
        label.className = 'div-label';
        label.textContent = child.name;
        div.appendChild(label);
        
        if (child.all_images.length > 0 && child.all_texts.length > 0) {
            div.style.display = 'flex';
            div.style.flexDirection = 'column';
            
            const textDiv = document.createElement('div');
            textDiv.className = 'text-content';
            textDiv.style.flex = '1';
            let textContent = '';
            for (const path of child.all_texts) {
                textContent += await loadText(path) + '\\n\\n';
            }
            const pre = document.createElement('pre');
            pre.textContent = textContent;
            textDiv.appendChild(pre);
            div.appendChild(textDiv);
            
            const imgDiv = document.createElement('div');
            imgDiv.style.flex = '1';
            imgDiv.style.position = 'relative';
            div.appendChild(imgDiv);
            setTimeout(() => createThreeScene(imgDiv, child.all_images), 0);
        } else if (child.all_images.length > 0) {
            setTimeout(() => createThreeScene(div, child.all_images), 0);
        } else if (child.all_texts.length > 0) {
            div.className = 'content-div text-content';
            let textContent = '';
            for (const path of child.all_texts) {
                textContent += await loadText(path) + '\\n\\n';
            }
            const pre = document.createElement('pre');
            pre.textContent = textContent;
            pre.style.marginTop = '30px';
            div.appendChild(pre);
        }
        
        contentDiv.appendChild(div);
    }
    console.log('DOM - canvas:', document.querySelectorAll('canvas').length, 'content-divs:', document.querySelectorAll('.content-div').length);

}
</script>
</body>
</html>''')

print("Generated spritesheets, data.json and index.html")
