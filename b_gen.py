from pathlib import Path
import json

def scan_folder(path, ignore=['venv', '__pycache__', '.git']):
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
        
        for child in children:
            images.extend(child['all_images'])
            texts.extend(child['all_texts'])
    
    content_type = 'empty'
    if images and texts:
        content_type = 'mixed'
    elif images:
        content_type = 'images'
    elif texts:
        content_type = 'text'
    
    return {
        'name': path.name,
        'path': str(path.relative_to('.')),
        'type': content_type,
        'children': children,
        'all_images': images,
        'all_texts': texts,
        'direct_children': children
    }

root = scan_folder(Path('.'))

with open('data.json', 'w') as f:
    json.dump(root, f, indent=2)

with open('index.html', 'w') as f:
    f.write('''<!DOCTYPE html>
<html>
<head>
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
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
let data;
let activeScenes = [];

fetch('data.json')
    .then(r => r.json())
    .then(d => {
        data = d;
        buildTree(data, document.getElementById('tree'));
    });

function buildTree(node, container, depth = 0) {
    const indent = '│   '.repeat(depth);
    const connector = '├── ';
    
    const item = document.createElement('div');
    item.className = 'tree-item';
    item.innerHTML = indent + connector;
    
    const link = document.createElement('span');
    link.className = 'tree-link';
    link.textContent = node.name;
    link.onclick = (e) => {
        e.stopPropagation();
        renderContent(node);
    };
    
    item.appendChild(link);
    container.appendChild(item);
    
    node.children.forEach(child => {
        buildTree(child, container, depth + 1);
    });
}

class OrbitControls {
    constructor(camera, domElement) {
        this.camera = camera;
        this.domElement = domElement;
        this.target = new THREE.Vector3();
        this.enabled = true;
        
        this.rotateSpeed = 1.0;
        this.zoomSpeed = 1.2;
        this.minDistance = 1;
        this.maxDistance = 100;
        
        this.theta = 0;
        this.phi = Math.PI / 2;
        this.radius = 10;
        
        this.isDragging = false;
        this.lastMouse = { x: 0, y: 0 };
        
        this.domElement.addEventListener('mousedown', this.onMouseDown.bind(this));
        this.domElement.addEventListener('mousemove', this.onMouseMove.bind(this));
        this.domElement.addEventListener('mouseup', this.onMouseUp.bind(this));
        this.domElement.addEventListener('wheel', this.onWheel.bind(this));
        
        this.update();
    }
    
    onMouseDown(e) {
        this.isDragging = true;
        this.lastMouse = { x: e.clientX, y: e.clientY };
    }
    
    onMouseMove(e) {
        if (!this.isDragging) return;
        
        const dx = e.clientX - this.lastMouse.x;
        const dy = e.clientY - this.lastMouse.y;
        
        this.theta -= dx * 0.005 * this.rotateSpeed;
        this.phi -= dy * 0.005 * this.rotateSpeed;
        this.phi = Math.max(0.1, Math.min(Math.PI - 0.1, this.phi));
        
        this.lastMouse = { x: e.clientX, y: e.clientY };
        this.update();
    }
    
    onMouseUp() {
        this.isDragging = false;
    }
    
    onWheel(e) {
        e.preventDefault();
        this.radius *= (e.deltaY > 0 ? 1.1 : 0.9);
        this.radius = Math.max(this.minDistance, Math.min(this.maxDistance, this.radius));
        this.update();
    }
    
    update() {
        const x = this.radius * Math.sin(this.phi) * Math.sin(this.theta);
        const y = this.radius * Math.cos(this.phi);
        const z = this.radius * Math.sin(this.phi) * Math.cos(this.theta);
        
        this.camera.position.set(x, y, z);
        this.camera.lookAt(this.target);
    }
}

function disposeScene(sceneData) {
    if (sceneData.animationId) {
        cancelAnimationFrame(sceneData.animationId);
    }
    if (sceneData.renderer) {
        sceneData.renderer.dispose();
        if (sceneData.renderer.domElement.parentNode) {
            sceneData.renderer.domElement.parentNode.removeChild(sceneData.renderer.domElement);
        }
    }
    if (sceneData.scene) {
        sceneData.scene.traverse(obj => {
            if (obj.geometry) obj.geometry.dispose();
            if (obj.material) {
                if (obj.material.map) obj.material.map.dispose();
                obj.material.dispose();
            }
        });
    }
}

function createThreeScene(container, images, label) {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setClearColor(0x000000);
    container.appendChild(renderer.domElement);
    
    const controls = new OrbitControls(camera, renderer.domElement);
    
    const cols = Math.ceil(Math.sqrt(images.length));
    const spacing = 2;
    
    images.forEach((imgPath, i) => {
        const row = Math.floor(i / cols);
        const col = i % cols;
        
        const loader = new THREE.TextureLoader();
        loader.load(imgPath, (texture) => {
            const aspect = texture.image.width / texture.image.height;
            const height = 1.5;
            const width = height * aspect;
            
            const geometry = new THREE.PlaneGeometry(width, height);
            const material = new THREE.MeshBasicMaterial({ map: texture });
            const mesh = new THREE.Mesh(geometry, material);
            
            mesh.position.x = (col - cols / 2) * spacing;
            mesh.position.y = -(row * spacing);
            
            scene.add(mesh);
            
            const edges = new THREE.EdgesGeometry(geometry);
            const line = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0xffffff }));
            line.position.copy(mesh.position);
            scene.add(line);
        });
    });
    
    camera.position.z = 10;
    controls.update();
    
    const sceneData = { scene, renderer, camera, controls, animationId: null };
    
    function animate() {
        sceneData.animationId = requestAnimationFrame(animate);
        renderer.render(scene, camera);
    }
    animate();
    
    activeScenes.push(sceneData);
    
    const resizeHandler = () => {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    };
    window.addEventListener('resize', resizeHandler);
    
    return sceneData;
}

async function loadText(path) {
    const res = await fetch(path);
    return await res.text();
}

async function renderContent(node) {
    activeScenes.forEach(disposeScene);
    activeScenes = [];
    
    const contentDiv = document.getElementById('content');
    contentDiv.innerHTML = '';
    
    const children = node.direct_children;
    
    if (children.length === 0) return;
    
    const childData = children.map(child => ({
        name: child.name,
        hasImages: child.all_images.length > 0,
        hasText: child.all_texts.length > 0,
        images: child.all_images,
        texts: child.all_texts
    }));
    
    contentDiv.style.flexDirection = 'row';
    
    for (const child of childData) {
        const div = document.createElement('div');
        div.className = 'content-div';
        div.style.flex = '1';
        div.style.display = 'flex';
        div.style.flexDirection = 'column';
        
        if (child.hasImages && child.hasText) {
            const textDiv = document.createElement('div');
            textDiv.className = 'content-div text-content';
            textDiv.style.flex = '1';
            const label1 = document.createElement('div');
            label1.className = 'div-label';
            label1.textContent = child.name + ' (text)';
            textDiv.appendChild(label1);
            
            let textContent = '';
            for (const path of child.texts) {
                textContent += await loadText(path) + '\\n\\n';
            }
            const pre = document.createElement('pre');
            pre.textContent = textContent;
            pre.style.marginTop = '30px';
            textDiv.appendChild(pre);
            div.appendChild(textDiv);
            
            const imgDiv = document.createElement('div');
            imgDiv.className = 'content-div';
            imgDiv.style.flex = '1';
            const label2 = document.createElement('div');
            label2.className = 'div-label';
            label2.textContent = child.name + ' (images)';
            imgDiv.appendChild(label2);
            div.appendChild(imgDiv);
            
            setTimeout(() => createThreeScene(imgDiv, child.images, child.name), 0);
        } else if (child.hasImages) {
            const label = document.createElement('div');
            label.className = 'div-label';
            label.textContent = child.name;
            div.appendChild(label);
            setTimeout(() => createThreeScene(div, child.images, child.name), 0);
        } else if (child.hasText) {
            div.className = 'content-div text-content';
            const label = document.createElement('div');
            label.className = 'div-label';
            label.textContent = child.name;
            div.appendChild(label);
            
            let textContent = '';
            for (const path of child.texts) {
                textContent += await loadText(path) + '\\n\\n';
            }
            const pre = document.createElement('pre');
            pre.textContent = textContent;
            pre.style.marginTop = '30px';
            div.appendChild(pre);
        }
        
        contentDiv.appendChild(div);
    }
}
</script>
</body>
</html>''')

print("Generated data.json and index.html")
