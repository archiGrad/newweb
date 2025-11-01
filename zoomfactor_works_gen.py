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

def scan_folder(path, ignore=['venv', '__pycache__', '.git', 'spritesheets', 'images']):
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
                elif item.suffix.lower() == '.html':
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
    is_gif = img_path.lower().endswith('.gif')
    
    if is_gif:
        gif = Image.open(img_path)
        frame_count = min(gif.n_frames, 20)
        
        if slot_idx + frame_count > 64:
            if slot_idx > 0:
                sheet.save(f'spritesheets/sprites_{sheet_idx}.png')
            sheet_idx += 1
            slot_idx = 0
            sheet = Image.new('RGBA', (2048, 2048), (0, 0, 0, 0))
        
        start_idx = slot_idx
        for frame_idx in range(frame_count):
            gif.seek(frame_idx)
            frame = gif.convert('RGBA')
            frame = resize_image(frame)
            
            col = slot_idx % 8
            row = slot_idx // 8
            x = col * 256 + 1
            y = row * 256 + 1
            sheet.paste(frame, (x, y))
            slot_idx += 1
        
        sprite_data[img_path] = {
            'spritesheet': f'spritesheets/sprites_{sheet_idx}.png',
            'start_index': start_idx,
            'frame_count': frame_count,
            'is_animated': True,
            'width': 256,
            'height': 256,
            'global_index': idx,
            'original_path': img_path
        }
    else:
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
<link rel="stylesheet" href="styles.css">
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

let dataTree;

let activeScenes = [];
const spritesheets = {};
const pendingLoads = {};
const materialCache = {};
const geometryCache = {};


fetch('data.json')
    .then(r => r.json())
    .then(d => {
        dataTree = d;
        buildTree(dataTree, document.getElementById('tree'));
    });




function buildTree(node, container, depth = 0, isLast = true, prefix = '') {
    const connector = isLast ? '└── ' : '├── ';
    const item = document.createElement('div');
    item.className = 'tree-item';
    item.innerHTML = prefix + connector;
    const link = document.createElement('span');
    link.className = 'tree-link';
    link.textContent = node.name;
    link.dataset.path = node.path;
    link.onclick = (e) => {
        e.stopPropagation();
        renderContent(node);
        updateTreeColors();
    };
    item.appendChild(link);
    container.appendChild(item);
    const newPrefix = prefix + (isLast ? '    ' : '│   ');
    node.children.forEach((child, i) => {
        buildTree(child, container, depth + 1, i === node.children.length - 1, newPrefix);
    });
}


function getDepthColor(depth) {
    const colors = ['#4f4', '#5e5', '#6d6', '#7c7', '#8b8', '#9a9', '#a9a', '#b8b', '#c7c', '#d6d'];
    return colors[Math.min(depth, 9)];
}

function updateTreeColors() {
    if (!currentNode) return;
    document.querySelectorAll('.tree-link').forEach(link => link.style.color = '#4af');
    const currentLink = document.querySelector(`.tree-link[data-path="${currentNode.path}"]`);
    if (currentLink) currentLink.style.color = '#44f';
    
    const pathParts = currentNode.path.split('/');
    for (let i = 1; i < pathParts.length; i++) {
        const ancestorPath = pathParts.slice(0, i).join('/');
        const ancestorLink = document.querySelector(`.tree-link[data-path="${ancestorPath}"]`);
        if (ancestorLink) ancestorLink.style.color = '#f44';
    }
    

    function colorDescendants(node, depth = 0) {
        node.children.forEach(child => {
            const childLink = document.querySelector(`.tree-link[data-path="${child.path}"]`);
            if (childLink) childLink.style.color = getDepthColor(depth);
            colorDescendants(child, depth + 1);
        });
    }
    colorDescendants(currentNode, 0);

}



function disposeScene(sceneData) {
    if (sceneData.animationId) cancelAnimationFrame(sceneData.animationId);
    if (sceneData.resizeHandler) window.removeEventListener('resize', sceneData.resizeHandler);
    if (sceneData.labelContainer && sceneData.labelContainer.parentNode) {
        sceneData.labelContainer.parentNode.removeChild(sceneData.labelContainer);
    }
    if (sceneData.countDiv && sceneData.countDiv.parentNode) {
        sceneData.countDiv.parentNode.removeChild(sceneData.countDiv);
    }
    if (sceneData.renderer) {
        sceneData.renderer.forceContextLoss();
        sceneData.renderer.dispose();
        if (sceneData.renderer.domElement.parentNode) {
            sceneData.renderer.domElement.parentNode.removeChild(sceneData.renderer.domElement);
        }
    }
    if (sceneData.scene) sceneData.scene.clear();
}


async function loadSpritesheet(path) {
    if (spritesheets[path]) return spritesheets[path];
    if (pendingLoads[path]) return pendingLoads[path];
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
    const grouped = {};

    const gridHelper = new THREE.GridHelper(20, 20, 0x444444, 0x222222);
    gridHelper.rotation.y = Math.PI / 2;
    scene.add(gridHelper);
    const axesHelper = new THREE.AxesHelper(5);
    scene.add(axesHelper);

    images.forEach(imgData => {
        const parts = imgData.original_path.split('/');
        const folder = parts.slice(0, -1).join('/') || 'root';

        if (!grouped[folder]) grouped[folder] = [];
        grouped[folder].push(imgData);
    });
    
    const folders = Object.keys(grouped);
    folders.forEach(folder => {
        grouped[folder].sort((a, b) => a.global_index - b.global_index);
    });
    
    const sharedGeometry = new THREE.PlaneGeometry(1, 1);
    const cols = Math.ceil(Math.sqrt(folders.length));
    const rows = Math.ceil(folders.length / cols);
    const spacing = 1.5;
    const offsetX = (cols - 1) * spacing / 2;
    const offsetZ = (rows - 1) * spacing / 2;



    let minX = Infinity, maxX = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;
    folders.forEach((folder, stackIdx) => {
        const row = Math.floor(stackIdx / cols);
        const col = stackIdx % cols;
        const xPos = col * spacing - offsetX;
        const zPos = row * spacing - offsetZ;
        minX = Math.min(minX, xPos);
        maxX = Math.max(maxX, xPos);
        minZ = Math.min(minZ, zPos);
        maxZ = Math.max(maxZ, zPos);
    });

    const geomWidth = maxX - minX;
    const geomDepth = maxZ - minZ;
    const maxDim = Math.max(geomWidth, geomDepth);
    const margin = 10;
    const baseFrustumSize = maxDim + margin;
    
    const minRandomZoom = 0.1;
    const maxRandomZoom = 2;
    const randomZoom = minRandomZoom + Math.random() * (maxRandomZoom - minRandomZoom);
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
    
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setClearColor(0x000000);
    container.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);


    let maxStackHeight = 0;
    folders.forEach(folder => {
        maxStackHeight = Math.max(maxStackHeight, grouped[folder].length * 0.1);
    });
    const midHeight = maxStackHeight / 2;
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

   
const updateCount = () => {
    const downColor = currentNode && currentNode.children.length > 0 ? '#4f4' : '#44f';
    countDiv.innerHTML = `<span style="cursor:pointer;padding:0 5px;user-select:none;color:#f44" id="nav-up">&#60;</span> ${loadedStacks}/${totalStacks} stacks | ${loadedImages}/${totalImages} images <span style="cursor:pointer;padding:0 5px;user-select:none;color:${downColor}" id="nav-down">&#62;</span>`;
};

updateCount();

countDiv.addEventListener('click', (e) => {
    if (e.target.id === 'nav-up') {
        if (currentNode && currentNode.path) {
            const parentPath = currentNode.path.split('/').slice(0, -1).join('/');
            const parentNode = findNodeByPath(dataTree, parentPath) || dataTree;
            renderContent(parentNode);
        }
    } else if (e.target.id === 'nav-down') {
        if (currentNode && currentNode.children.length > 0) {
            renderContent(currentNode.children[0]);
        }
    }
});







 
    const stackLabels = [];

    (async () => {
        for (let stackIdx = 0; stackIdx < folders.length; stackIdx++) {
            const folderName = folders[stackIdx];
            const stackImages = grouped[folderName];
            const row = Math.floor(stackIdx / cols);
            const col = stackIdx % cols;
            const xPos = col * spacing - offsetX;
            const zPos = row * spacing - offsetZ;

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
                const aspect = imgData.width / imgData.height;
                const height = 1.5;
                const width = height * aspect;
                const mesh = new THREE.Mesh(sharedGeometry, materialCache[imgData.spritesheet]);
                mesh.scale.set(width, height, 1);
                mesh.position.x = xPos;
                mesh.position.y = i * 0.1;
                mesh.position.z = zPos;
                mesh.rotation.x = Math.PI / 2;
                mesh.rotation.y = Math.PI;
                mesh.rotation.z = Math.PI;
                if (imgData.is_animated) {
                    mesh.userData = {
                        imgData: imgData,
                        spritesheet: imgData.spritesheet
                    };
                    mesh.onBeforeRender = function() {
                        const frame = Math.floor(Date.now() / 100) % this.userData.imgData.frame_count;
                        const idx = this.userData.imgData.start_index + frame;
                        const sprite_col = idx % 8;
                        const sprite_row = Math.floor(idx / 8);
                        const u_start = (sprite_col * 256 + 1) / 2048;
                        const u_end = u_start + 256 / 2048;
                        const v_start = 1 - ((sprite_row + 1) * 256 + 1) / 2048;
                        const v_end = 1 - (sprite_row * 256 + 1) / 2048;
                        const uvs = this.geometry.attributes.uv;
                        uvs.setXY(0, u_start, v_end);
                        uvs.setXY(1, u_end, v_end);
                        uvs.setXY(2, u_start, v_start);
                        uvs.setXY(3, u_end, v_start);
                        uvs.needsUpdate = true;
                    };
                    mesh.geometry = sharedGeometry.clone();
                } else {
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
                    mesh.geometry = geometryCache[uvKey];
                }
                scene.add(mesh);
                loadedImages++;
                updateCount();
                await new Promise(resolve => setTimeout(resolve, 1));
            }

            loadedStacks++;
            updateCount();
            const topY = (stackImages.length - 1) * 0.1;
            const worldPos = new THREE.Vector3(xPos, topY, zPos);
            const label = document.createElement('span');


const currentPath = currentNode ? currentNode.path : '';
const currentFolderName = currentPath ? currentPath.split('/').pop() : '';
const relativePath = folderName.startsWith(currentPath) && currentPath 
    ? folderName.slice(currentPath.length + 1) 
    : folderName;
const pathParts = relativePath.split('/').filter(p => p);
const displayParts = currentPath ? ['..', currentFolderName, ...pathParts] : pathParts;
label.innerHTML = displayParts.map((part, idx) => {
    let color = '#4af';
    let partPath = '';
    
    if (part === '..') {
        partPath = currentPath.split('/').slice(0, -1).join('/');
        color = '#f44';
    } else if (idx === 1 && currentPath) {
        partPath = currentPath;
        color = '#44f';
  

    } else {
        partPath = currentPath ? currentPath + '/' + pathParts.slice(0, idx - 1).join('/') : pathParts.slice(0, idx).join('/');
        const relativeDepth = idx - 2;
        color = getDepthColor(relativeDepth);
    }
    
 
    return `<span style="background:black;padding:2px 4px;cursor:pointer;margin-right:2px;color:${color}" data-path="${partPath}">${part}</span>`;
}).join('/') + `<span style="background:black;padding:2px 4px;font-size:9px;margin-left:2px">${stackImages.length}</span>`;


            label.style.position = 'absolute';
            label.style.pointerEvents = 'auto';
            label.style.cursor = 'pointer';
            label.onclick = () => {
                const folderNode = findNodeByPath(dataTree, folderName);
                if (folderNode) renderContent(folderNode);
            };
            label.style.color = 'white';
            label.style.fontFamily = 'monospace';
            label.style.fontSize = '11px';
            labelContainer.appendChild(label);



            stackLabels.push({ element: label, position: worldPos, xPos, zPos, folderName });
            label.style.pointerEvents = 'auto';
            label.querySelectorAll('span[data-path]').forEach(span => {
                span.onclick = (e) => {
                    e.stopPropagation();
                    const node = findNodeByPath(dataTree, span.dataset.path);
                    if (node) renderContent(node);
                };
            });

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

const sceneData = { scene, renderer, camera, controls, animationId: null, resizeHandler, stats, labelContainer, countDiv };

    function animate() {
        stats.begin();
        sceneData.animationId = requestAnimationFrame(animate);
        controls.update();
        const rotationAngle = Date.now() * 0.0001;
        scene.rotation.y = rotationAngle;
        stackLabels.forEach(({ element, position, xPos, zPos }) => {
            const rotatedX = xPos * Math.cos(rotationAngle) + zPos * Math.sin(rotationAngle);
            const rotatedZ = -xPos * Math.sin(rotationAngle) + zPos * Math.cos(rotationAngle);
            const rotatedPos = new THREE.Vector3(rotatedX, position.y, rotatedZ);
            const screenPos = rotatedPos.project(camera);
            const x = (screenPos.x * 0.5 + 0.5) * container.clientWidth;
            const y = (-(screenPos.y * 0.5) + 0.5) * container.clientHeight;
            element.style.left = x + 'px';
            element.style.top = y + 'px';
        });        
        renderer.render(scene, camera);
        stats.end();
    }
    animate();

    activeScenes.push(sceneData);
    window.addEventListener('resize', resizeHandler);
}

async function loadText(path) {
    const res = await fetch(path);
    return await res.text();
}

function findNodeByPath(node, targetPath) {
    if (node.path === targetPath || node.name === targetPath) return node;
    for (const child of node.children) {
        const found = findNodeByPath(child, targetPath);
        if (found) return found;
    }
    return null;
}

let currentNode = null;

async function renderContent(node) {
    currentNode = node;
    updateTreeColors();

    activeScenes.forEach(disposeScene);
    activeScenes = [];
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
        const pathParts = child.path.split('/');
        label.innerHTML = pathParts.map((part, idx) => {
            const partPath = pathParts.slice(0, idx + 1).join('/');
            let color = '#4af';
            if (currentNode) {
                if (partPath === currentNode.path) color = '#44f';
                else if (currentNode.path.startsWith(partPath + '/')) color = '#f44';
                else if (currentNode.children.some(c => c.path === partPath)) color = '#4f4';
            }
            return `<span style="color:${color};cursor:pointer" data-path="${partPath}">${part}</span>`;
        }).join('/');
        label.style.pointerEvents = 'auto';
        label.querySelectorAll('span[data-path]').forEach(span => {
            span.onclick = (e) => {
                e.stopPropagation();
                const node = findNodeByPath(dataTree, span.dataset.path);
                if (node) renderContent(node);
            };
        });
        

        div.appendChild(label);








if (child.all_images.length > 0 && child.all_texts.length > 0) {
    div.style.display = 'flex';
    div.style.flexDirection = 'row';
    const textDiv = document.createElement('div');
    textDiv.className = 'text-content';
    textDiv.style.flex = '1';
    textDiv.style.border = '1px solid white';
    textDiv.style.position = 'relative';
    textDiv.style.overflow = 'auto';
    let htmlContent = '';
    for (const path of child.all_texts) {
        htmlContent += await loadText(path);
    }
    
    const hasParent = currentNode.path.split('/').length > 1;
    const firstChildWithText = currentNode.children?.find(c => c.all_texts.length > 0);
    const leftColor = hasParent ? '#f44' : '#44f';
    const rightColor = firstChildWithText ? '#4f4' : '#44f';
    
    textDiv.innerHTML = htmlContent + `<div style="position:absolute;bottom:5px;right:5px;color:white;font-family:monospace;font-size:11px;background:black;padding:2px 5px;border:1px solid white;z-index:100"><span style="cursor:pointer;padding:0 5px;user-select:none;color:${leftColor}" class="text-nav-left">&#60;</span><span style="padding:0 2px">texts</span><span style="cursor:pointer;padding:0 5px;user-select:none;color:${rightColor}" class="text-nav-right">&#62;</span></div>`;

   
    const navLeft = textDiv.querySelector('.text-nav-left');
    const navRight = textDiv.querySelector('.text-nav-right');
    
    navLeft.onclick = () => {
        if (currentNode && currentNode.path) {
            const parentPath = currentNode.path.split('/').slice(0, -1).join('/');
            const parentNode = findNodeByPath(dataTree, parentPath) || dataTree;
            if (parentNode && parentNode.all_texts.length > 0) {
                renderContent(parentNode);
            }
        }
    };
    
    navRight.onclick = () => {
        if (currentNode && currentNode.children && currentNode.children.length > 0) {
            const firstChildWithText = currentNode.children.find(c => c.all_texts.length > 0);
            if (firstChildWithText) {
                renderContent(firstChildWithText);
            }
        }
    };
    
    div.appendChild(textDiv);
    const imgDiv = document.createElement('div');
    imgDiv.style.flex = '1';
    imgDiv.style.position = 'relative';
    imgDiv.style.border = '1px solid white';
    div.appendChild(imgDiv);
    setTimeout(() => createThreeScene(imgDiv, child.all_images), 0);

        } else if (child.all_images.length > 0) {
            setTimeout(() => createThreeScene(div, child.all_images), 0);



   



} else if (child.all_texts.length > 0) {
    div.className = 'content-div text-content';
    div.style.position = 'relative';
    let htmlContent = '';
    for (const path of child.all_texts) {
        htmlContent += await loadText(path);
    }
    
    const pathParts = child.path.split('/');
    const labelHtml = pathParts.map((part, idx) => {
        const partPath = pathParts.slice(0, idx + 1).join('/');
        let color = '#4af';
        if (currentNode) {
            if (partPath === currentNode.path) color = '#44f';
            else if (currentNode.path.startsWith(partPath + '/')) color = '#f44';
            else if (currentNode.children.some(c => c.path === partPath)) color = '#4f4';
        }
        return `<span style="color:${color};cursor:pointer" data-path="${partPath}">${part}</span>`;
    }).join('/');
    
    const navHtml = `<div style="position:absolute;bottom:5px;right:5px;color:white;font-family:monospace;font-size:11px;background:black;padding:2px 5px;border:1px solid white"><span style="cursor:pointer;padding:0 5px;user-select:none;color:#4af" class="text-nav-left">&#60;</span><span style="padding:0 2px">texts</span><span style="cursor:pointer;padding:0 5px;user-select:none;color:#4af" class="text-nav-right">&#62;</span></div>`;
    
    div.innerHTML = htmlContent + '<style>.div-label { position: absolute; top: 5px; left: 5px; background: black; padding: 2px 5px; border: 1px solid white; z-index: 100; pointer-events: auto; }</style><div class="div-label">' + labelHtml + '</div>' + navHtml;
    
    const textLabel = div.querySelector('.div-label');
    textLabel.querySelectorAll('span[data-path]').forEach(span => {
        span.onclick = (e) => {
            e.stopPropagation();
            const node = findNodeByPath(dataTree, span.dataset.path);
            if (node) renderContent(node);
        };
    });
    
    const navLeft = div.querySelector('.text-nav-left');
    const navRight = div.querySelector('.text-nav-right');
    
    navLeft.onclick = () => {
        if (currentNode && currentNode.path) {
            const parentPath = currentNode.path.split('/').slice(0, -1).join('/');
            const parentNode = findNodeByPath(dataTree, parentPath) || dataTree;
            if (parentNode && parentNode.all_texts.length > 0) {
                renderContent(parentNode);
            }
        }
    };
    
    navRight.onclick = () => {
        if (currentNode && currentNode.children && currentNode.children.length > 0) {
            const firstChildWithText = currentNode.children.find(c => c.all_texts.length > 0);
            if (firstChildWithText) {
                renderContent(firstChildWithText);
            }
        }
    };
}




















        contentDiv.appendChild(div);
    }
}
</script>
</body>
</html>''')

print("Generated spritesheets, data.json and index.html")
