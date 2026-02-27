from pathlib import Path
import json
import ast
from PIL import Image, ImageDraw, ImageFont
from natsort import natsorted

# ==========================================
# GLOBAL DEFAULT CONFIGURATION
# ==========================================

DEFAULTS = {
    'SPRITESHEET_SIZE': 1024 * 4,
    'SPRITE_SIZE': 64,
    'RESIZE_METHOD': Image.LANCZOS,
    'SPRITESHEET_FORMAT': 'webp',
    
    # Image Processing Defaults
    'SHARPEN': False,
    'SHARPEN_RADIUS': 1,
    'SHARPEN_PERCENT': 20,
    'SHARPEN_THRESHOLD': 3,

    'GAUSSIAN_BLUR': False,
    'GAUSSIAN_BLUR_RADIUS': 2,
    
    'COLOR_TO_TRANSPARENT': 'blue',
    'COLOR_THRESHOLD': 30,

    'DITHERING': False,
    'DITHER_MODE': 'custom_palette',
    'DITHER_METHOD': 'ordered',
    'DITHER_COLORS': 256,
    'CUSTOM_PALETTE': ['#000000', '#FF0000', '#00FF00'],

    'MAX_GIF_FRAMES': 30,
    'GIF_SPEED': 0.6, 


    # Folder Label Defaults (Renamed & Updated)
    'IMAGE_SETTINGS_LABELS': True,       # Was IMAGE_FOLDERNAME
    'IMAGE_SETTINGS_COLOR': 'white',     # Was IMAGE_FOLDERNAME_COLOR
    'IMAGE_SETTINGS_FONTSIZE': 3,       # Was IMAGE_FOLDERNAME_FONTSIZE
    'IMAGE_SETTINGS_CUSTOMTEXT': "",     # NEW: Custom text override
    'TEXT_IMAGE_RESOLUTION': 256,        # NEW: Fixed resolution for text labels
    'LABEL_SPRITE_SIZE': 512,            # Sprite size for top/bottom label images on spritesheets
    'LOD_TARGET_SPRITE_SIZES': [None, 32, 8],  # Target sprite px per LOD level (None = original)

    #square image processing or not
    'SQUARE_IMAGES': True,
   
    # Viewer Config
    'STACK_SPACING': 0.09,
    'STACK_DIM_OPACITY': 0.35, 
    'SEED': 2922,
    'QUICKLOAD_THRESHOLD': 100,
    'ORDERED_GRID_LAYOUT': True,
    'ROTATION_SPEED': 0.000015,
    'RANDOM_ZOOM': False,
    'ZOOM_VALUE': 0.4,
    'RANDOM_TEXTDIV_POSITION': False,
    'LOADINGSCREEN_IMG_INCREMENT': 50,

    #stack labels/annotations 
    'MAX_LABELS': 200,
    'SCREEN_BUFFER': 100,
    'COLORED_HTML_DOTS': True,
    'BREADCRUMB_HTML_DOTS': False,
    'SHOW_NAV_ACCESSORIES': False,
    'SUBMENU_CLOSE_DELAY': 400

}

# ==========================================
# CONFIGURATION PARSING
# ==========================================

def parse_custom_processing(path, current_config):
    new_config = current_config.copy()
    
    sprite_size_file = path / '.sprite_size'
    if sprite_size_file.exists():
        try:
            val = int(sprite_size_file.read_text().strip())
            new_config['SPRITE_SIZE'] = val
        except:
            print(f"Warning: Invalid .sprite_size in {path}")

    custom_file = path / '.custom_processing'
    if custom_file.exists():
        try:
            content = custom_file.read_text()
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith('#'): continue
                if '=' in line:
                    key, value = [x.strip() for x in line.split('=', 1)]
                    if key in DEFAULTS:
                        try:
                            new_config[key] = ast.literal_eval(value)
                        except:
                            new_config[key] = value
        except Exception as e:
            print(f"Warning: Error parsing .custom_processing in {path}: {e}")
            
    return new_config


# ==========================================
# IMAGE PROCESSING FUNCTIONS
# ==========================================

def apply_filter(img, conf):
    if conf['SHARPEN']:
        from PIL import ImageFilter
        img = img.filter(ImageFilter.UnsharpMask(
            radius=conf['SHARPEN_RADIUS'],
            percent=conf['SHARPEN_PERCENT'],
            threshold=conf['SHARPEN_THRESHOLD']
        )) 

    if conf['GAUSSIAN_BLUR']:
        from PIL import ImageFilter
        img = img.filter(ImageFilter.GaussianBlur(radius=conf['GAUSSIAN_BLUR_RADIUS']))
    
    if conf['COLOR_TO_TRANSPARENT']:
        colors = {
            'black': (0, 0, 0), 'white': (255, 255, 255), 'red': (255, 0, 0),
            'green': (0, 255, 0), 'blue': (0, 0, 255), 'yellow': (255, 255, 0),
            'cyan': (0, 255, 255), 'magenta': (255, 0, 255), 'light_gray': (192, 192, 192),
            'dark_gray': (64, 64, 64), 'orange': (255, 165, 0), 'purple': (128, 0, 128)
        }
        target = conf['COLOR_TO_TRANSPARENT']
        if target in colors:
            target_r, target_g, target_b = colors[target]
            img = img.convert('RGBA')
            pixels = img.load()
            thresh = conf['COLOR_THRESHOLD']
            for y in range(img.height):
                for x in range(img.width):
                    r, g, b, a = pixels[x, y]
                    if (abs(r - target_r) < thresh and 
                        abs(g - target_g) < thresh and 
                        abs(b - target_b) < thresh):
                        pixels[x, y] = (r, g, b, 0)
    
    if conf['DITHERING']:
        dither_map = {
            'floyd_steinberg': Image.Dither.FLOYDSTEINBERG,
            'ordered': Image.Dither.ORDERED,
            'none': Image.Dither.NONE
        }
        
        has_alpha = img.mode == 'RGBA'
        alpha_channel = img.split()[3] if has_alpha else None
        
        if conf['DITHER_MODE'] == 'bw':
            rgb_img = img.convert('L')
            dithered = rgb_img.convert('1', dither=dither_map[conf['DITHER_METHOD']])
            dithered = dithered.convert('RGB')
        
        elif conf['DITHER_MODE'] == 'color_reduce':
            rgb_img = img.convert('RGB')
            dithered = rgb_img.quantize(colors=conf['DITHER_COLORS'], dither=dither_map[conf['DITHER_METHOD']])
            dithered = dithered.convert('RGB')
        
        elif conf['DITHER_MODE'] == 'custom_palette':
            palette_colors = []
            for hex_color in conf['CUSTOM_PALETTE']:
                hex_color = hex_color.lstrip('#')
                r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                palette_colors.extend([r, g, b])
            
            while len(palette_colors) < 768:
                palette_colors.extend([0, 0, 0])
            
            palette_img = Image.new('P', (1, 1))
            palette_img.putpalette(palette_colors)
            
            rgb_img = img.convert('RGB')
            dithered = rgb_img.quantize(palette=palette_img, dither=dither_map[conf['DITHER_METHOD']])
            dithered = dithered.convert('RGB')
        
        if has_alpha:
            dithered = dithered.convert('RGBA')
            dithered.putalpha(alpha_channel)
        
        img = dithered
    
    return img

def resize_image(img, target_size, conf=None):
    force_square = conf.get('SQUARE_IMAGES', False) if conf else DEFAULTS['SQUARE_IMAGES']
    
    if force_square:
        if img.size != (target_size, target_size):
            img = img.resize((target_size, target_size), DEFAULTS['RESIZE_METHOD'])
        return img

    # Original Logic (Preserve Aspect Ratio)
    w, h = img.size
    longest = max(w, h)
    if longest != target_size:
        scale = target_size / longest
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = img.resize((new_w, new_h), DEFAULTS['RESIZE_METHOD'])
    return img

# ==========================================
# FILE SCANNING
# ==========================================



def scan_folder(path, parent_hidden=False, inherited_spacing=None, inherited_zoom=None, inherited_keywords=None, ignore=['venv', '__pycache__', '.git', 'fonts',  'spritesheets', 'images', 'backup', 'geo']):
    if path.name in ignore:
        return None
    
    images = []
    texts = []
    children = []
    grid_layout = None
    no_accum = False
    stop_accum = False
    
    manual_spacing = inherited_spacing
    manual_zoom = inherited_zoom
    keywords = list(inherited_keywords) if inherited_keywords else []
    
    is_hidden = parent_hidden or (path / '.hidden').exists()
    
    if path.is_dir():
        kw_file = path / '.keywords'
        if kw_file.exists():
            try:
                lines = [l.strip() for l in kw_file.read_text().splitlines() if l.strip() and not l.strip().startswith('#')]
                keywords.extend(lines)
            except Exception as e:
                print(f"Warning: Error reading .keywords in {path}: {e}")

        grid_file = path / '.grid_layout'
        if grid_file.exists():
            grid_layout = grid_file.read_text().strip()
        
        # Check .custom_processing for STACK_SPACING
        custom_file = path / '.custom_processing'
        if custom_file.exists():
            try:
                content = custom_file.read_text()
                for line in content.splitlines():
                    line = line.strip()
                    if not line or line.startswith('#'): continue
                    if '=' in line:
                        key, value = [x.strip() for x in line.split('=', 1)]
                        if key == 'STACK_SPACING':
                            try:
                                manual_spacing = ast.literal_eval(value)
                            except:
                                pass
                        if key == 'ZOOM_VALUE':
                            try:
                                manual_zoom = float(ast.literal_eval(value))
                            except:
                                pass
            except:
                pass
        
        # .stack_spacing file overrides .custom_processing
        spacing_file = path / '.stack_spacing'
        if spacing_file.exists():
            try:
                manual_spacing = float(spacing_file.read_text().strip())
            except Exception as e:
                print(f"Warning: Invalid .stack_spacing in {path}: {e}")
        
        no_accum = (path / '.html_only_here').exists()
        stop_accum = (path / '.html_stops_here').exists()
            
        for item in natsorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
            if item.name in ignore or item.name.startswith('.'): 
                continue
            if item.is_file():
                if item.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                    images.append(item.relative_to('.').as_posix())
                elif item.suffix.lower() == '.html':
                    texts.append(item.relative_to('.').as_posix())
            elif item.is_dir():
                child = scan_folder(item, parent_hidden=is_hidden, inherited_spacing=manual_spacing, inherited_zoom=manual_zoom, inherited_keywords=keywords, ignore=ignore)
                if child:
                    children.append(child)
        
        all_images = images.copy()
        all_texts = texts.copy()
        if not stop_accum:
            for child in children:
                all_images.extend(child['ai'])
                if not child.get('na', False) and not child.get('sa', False):
                    all_texts.extend(child['at'])
        else:
            for child in children:
                all_images.extend(child['ai'])        

    content_type = 'empty'
    if all_images and all_texts: content_type = 'mixed'
    elif all_images: content_type = 'images'
    elif all_texts: content_type = 'text'
    
    result = {
        'name': path.name,
        'path': path.relative_to('.').as_posix(),
        'type': content_type,
        'children': children,
        'ai': all_images, 
        'at': all_texts,
        'oi': images,
        'ot': texts,
        'na': no_accum,
        'sa': stop_accum,
        'hid': is_hidden,
        'msp': manual_spacing,
        'mzm': manual_zoom,
        'sk': keywords if keywords else []
    }
    if grid_layout: result['grid_layout'] = grid_layout
    return result


# root = scan_folder(Path('.'))
# root['name'] = Path('.').resolve().name or "Root"


# Check if the specific project folder exists and use it as the root
target_root = Path('archiGrad.io')

if target_root.exists() and target_root.is_dir():
    root = scan_folder(target_root, inherited_spacing=None)


# ==========================================
# LABEL GENERATION
# ==========================================

def load_custom_font(size):
    # 1. Check specifically for the requested font in ./fonts/
    requested_font = Path('fonts/UbuntuMono-Regular.ttf')
    if requested_font.exists():
        try:
            return ImageFont.truetype(str(requested_font), int(size))
        except IOError:
            print(f"Warning: Found {requested_font} but could not load it.")
            
    # 2. Fallback List
    font_candidates = [
        "UbuntuMono-Regular.ttf", 
        "UbuntuMono-R.ttf",
        "DejaVuSansMono.ttf", 
        "FreeMono.ttf", 
        "Consolas.ttf",
        "arial.ttf"
    ]
    
    for font_name in font_candidates:
        try:
            return ImageFont.truetype(font_name, int(size))
        except IOError:
            continue
            
    # 3. Final Fallback
    try:
        return ImageFont.load_default(size=int(size))
    except TypeError:
        return ImageFont.load_default()

def get_dotfile_content(path):
    ignored_dotfiles = [
        '.html_only_here', '.html_stops_here', '.hidden', 
        '.DS_Store', '.git', '.gitignore', '__pycache__'
    ]
    
    candidates = []
    try:
        for item in path.iterdir():
            if item.is_file() and item.name.startswith('.') and item.name not in ignored_dotfiles:
                candidates.append(item)
    except Exception:
        pass
    
    if not candidates:
        return None
        
    target = sorted(candidates, key=lambda x: x.name)[0]
    
    try:
        content = target.read_text(encoding='utf-8')
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        
        if not lines:
            return None
            
        return {'name': target.name, 'lines': lines}
    except Exception as e:
        print(f"Error reading dotfile {target}: {e}")
        return None

def create_label_image(title, body_lines, color, output_path, img_resolution, font_size):
    try:
        # Use the passed resolution
        img = Image.new('RGBA', (img_resolution, img_resolution), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Use the scaled font size
        font_title = load_custom_font(int(font_size * 1.5))
        font_body = load_custom_font(int(font_size))
        
        def get_text_size(text, font):
            try:
                left, top, right, bottom = font.getbbox(text)
                return right - left, bottom - top
            except AttributeError:
                return font.getsize(text)

        # Layout Configuration
        scale_factor = img_resolution / 64.0
        padding_left = int(10 * scale_factor)
        padding_top = int(10 * scale_factor)
        
        # --- CHANGED: Set spacing to minimum (0) ---
        line_spacing = 0 
        title_body_gap = int(2 * scale_factor) if (title and body_lines) else 0
        # -------------------------------------------
        
        current_y = padding_top
        
        if title:
            draw.text((padding_left, current_y), title, fill=color, font=font_title)
            title_w, title_h = get_text_size(title, font_title)
            current_y += title_h + title_body_gap
        
        for line in body_lines:
            draw.text((padding_left, current_y), line, fill=color, font=font_body)
            line_w, line_h = get_text_size(line, font_body)
            current_y += line_h + line_spacing
            
        img.save(output_path)
        return True
    except Exception as e:
        print(f"Error creating label {output_path}: {e}")
        return False

def is_label_image(filename):
    return (filename.startswith('ZZ_') and filename.endswith('_top.png')) or \
           (filename.startswith('AA_') and filename.endswith('_bottom.png'))

def manage_folder_labels(node, parent_config):
    node_path = Path(node['path'])
    current_config = parse_custom_processing(node_path, parent_config)
    
    folder_name = node['name']
    top_name = f"ZZ_{folder_name}_top.png"
    bottom_name = f"AA_{folder_name}_bottom.png"
    
    for f in node_path.iterdir():
        if f.is_file() and is_label_image(f.name) and f.name not in [top_name, bottom_name]:
            try: f.unlink()
            except: pass
    
    top_path = node_path / top_name
    bottom_path = node_path / bottom_name
    
    real_images = []
    for img_str in node['oi']:
        if not is_label_image(Path(img_str).name):
            real_images.append(img_str)
    
    real_images = natsorted(real_images, key=lambda x: Path(x).name)
            
    should_generate = current_config.get('IMAGE_SETTINGS_LABELS', False)
    has_real_images = len(real_images) > 0
    
    new_oi_list = []

    if should_generate and has_real_images:
        color = current_config.get('IMAGE_SETTINGS_COLOR', 'white')
        
        # Configs from user/dotfile
        base_font_size = current_config.get('IMAGE_SETTINGS_FONTSIZE', 16)
        custom_text = current_config.get('IMAGE_SETTINGS_CUSTOMTEXT', "")
        
        # FORCE High Resolution
        text_resolution = DEFAULTS['TEXT_IMAGE_RESOLUTION']
        
        # SCALE Font Size
        font_scale = text_resolution / 64.0
        effective_font_size = int(base_font_size * font_scale)
        
        # -------------------------------------------------
        # PRIORITY LOGIC
        # -------------------------------------------------
        if custom_text and custom_text.strip():
            lines = custom_text.strip().splitlines()
            top_title = ""
            top_body = lines
            bottom_title = ""
            bottom_body = lines
        else:
            dotfile_data = get_dotfile_content(node_path)
            if dotfile_data:
                top_title = dotfile_data['name']
                top_body = dotfile_data['lines']
                bottom_title = dotfile_data['name']
                bottom_body = dotfile_data['lines']
            else:
                top_title = folder_name
                top_body = ["top"]
                bottom_title = folder_name
                bottom_body = ["bottom"]
        
        if create_label_image(bottom_title, bottom_body, color, bottom_path, text_resolution, effective_font_size):
            # new_oi_list.append(str(bottom_path.relative_to('.')))
            new_oi_list.append(bottom_path.relative_to('.').as_posix())
        
        new_oi_list.extend(real_images)
        
        if create_label_image(top_title, top_body, color, top_path, text_resolution, effective_font_size):
            # new_oi_list.append(str(top_path.relative_to('.')))
            new_oi_list.append(top_path.relative_to('.').as_posix())
            
        node['oi'] = new_oi_list
        
    else:
        node['oi'] = real_images

    for child in node['children']:
        manage_folder_labels(child, current_config)

# Execute Label Generation
manage_folder_labels(root, DEFAULTS)


# ==========================================
# FLATTENING AND CONFIG ASSIGNMENT
# ==========================================

all_image_items = [] 

def collect_images_with_config(node, parent_config):
    node_path = Path(node['path'])
    current_config = parse_custom_processing(node_path, parent_config)
    
    label_conf = None
    for img_path in node['oi']:
        if is_label_image(Path(img_path).name):
            if not label_conf:
                label_conf = current_config.copy()
                label_conf['SPRITE_SIZE'] = current_config.get('LABEL_SPRITE_SIZE', DEFAULTS['LABEL_SPRITE_SIZE'])
            all_image_items.append({'path': img_path, 'conf': label_conf})
        else:
            all_image_items.append({'path': img_path, 'conf': current_config})
        
    for child in node['children']:
        collect_images_with_config(child, current_config)

collect_images_with_config(root, DEFAULTS)

all_image_items.sort(key=lambda x: (x['conf']['SPRITE_SIZE'], x['path']))

# ==========================================
# SPRITESHEET GENERATION
# ==========================================

Path('spritesheets').mkdir(exist_ok=True)
for file in Path('spritesheets').glob('*'):
    file.unlink()

LOD_LEVELS = 3
LOD_TARGET_SPRITE_SIZES = DEFAULTS['LOD_TARGET_SPRITE_SIZES']

sprite_data = {} 
sheet_idx = 0
current_sheet_size = 0 
sheet = None
slot_idx = 0
saved_sheets = []

def save_sheet_with_lod(sheet, sheet_idx, sprite_size):
    fmt = DEFAULTS['SPRITESHEET_FORMAT']
    base_path = f'spritesheets/sprites_{sheet_idx}_lod0.{fmt}'
    sheet.save(base_path)
    for lod in range(1, LOD_LEVELS):
        target_sprite = LOD_TARGET_SPRITE_SIZES[lod]
        if target_sprite >= sprite_size:
            scale_factor = 1.0
        else:
            scale_factor = target_sprite / sprite_size
        new_size = max(1, int(sheet.width * scale_factor))
        lod_sheet = sheet.resize((new_size, new_size), Image.LANCZOS)
        lod_sheet.save(f'spritesheets/sprites_{sheet_idx}_lod{lod}.{fmt}')
    saved_sheets.append(sheet_idx)
    lod1_size = max(1, int(sheet.width * min(1.0, LOD_TARGET_SPRITE_SIZES[1] / sprite_size)))
    lod2_size = max(1, int(sheet.width * min(1.0, LOD_TARGET_SPRITE_SIZES[2] / sprite_size)))
    print(f"  Saved spritesheet {sheet_idx} (sprite_size={sprite_size}) with {LOD_LEVELS} LOD levels ({sheet.width}px -> {lod1_size}px -> {lod2_size}px)")

def lod_paths(sheet_idx):
    fmt = DEFAULTS['SPRITESHEET_FORMAT']
    return [f'spritesheets/sprites_{sheet_idx}_lod{lod}.{fmt}' for lod in range(LOD_LEVELS)]

for item in all_image_items:
    img_path = item['path']
    conf = item['conf']
    
    target_size = conf['SPRITE_SIZE']
    sheet_dim = conf['SPRITESHEET_SIZE']
    
    sprites_per_row = sheet_dim // target_size
    sprites_per_sheet = sprites_per_row * sprites_per_row
    
    if sheet is None or target_size != current_sheet_size or slot_idx >= sprites_per_sheet:
        if sheet is not None:
            save_sheet_with_lod(sheet, sheet_idx, current_sheet_size)
            sheet_idx += 1
        
        sheet = Image.new('RGBA', (sheet_dim, sheet_dim), (0, 0, 0, 0))
        slot_idx = 0
        current_sheet_size = target_size

    speed_val = max(0.0, min(1.0, conf['GIF_SPEED']))
    gif_delay_ms = int(500 - (speed_val * 480))

    is_gif = img_path.lower().endswith('.gif')
    
    if is_gif:
        try:
            gif = Image.open(img_path)
            frame_count = min(gif.n_frames, conf['MAX_GIF_FRAMES']) 
            
            if slot_idx + frame_count > sprites_per_sheet:
                save_sheet_with_lod(sheet, sheet_idx, current_sheet_size)
                sheet_idx += 1
                sheet = Image.new('RGBA', (sheet_dim, sheet_dim), (0, 0, 0, 0))
                slot_idx = 0
            
            start_idx = slot_idx
            for frame_idx in range(frame_count):
                gif.seek(frame_idx)
                frame = gif.convert('RGBA')
                frame = resize_image(frame, target_size, conf)
                frame = apply_filter(frame, conf)           
    
                col = slot_idx % sprites_per_row
                row = slot_idx // sprites_per_row
                x = col * target_size
                y = row * target_size
                sheet.paste(frame, (x, y))
                slot_idx += 1
            
            sprite_data[img_path] = {
                'ss': lod_paths(sheet_idx),
                'si': start_idx,
                'fc': frame_count,
                'anim': True,
                'w': target_size,
                'h': target_size,
                'sz': target_size,
                'gd': gif_delay_ms,
                'path': img_path
            }
        except Exception as e:
            print(f"Error processing GIF {img_path}: {e}")
    else:
        try:
            img = Image.open(img_path).convert('RGBA')
            img = resize_image(img, target_size, conf)
            img = apply_filter(img, conf)       
    
            col = slot_idx % sprites_per_row
            row = slot_idx // sprites_per_row
            x = col * target_size
            y = row * target_size
            sheet.paste(img, (x, y))
            
            sprite_data[img_path] = {
                'ss': lod_paths(sheet_idx),
                'idx': slot_idx,
                'w': img.width,
                'h': img.height,
                'sz': target_size,
                'path': img_path
            }
            slot_idx += 1
        except Exception as e:
            print(f"Error processing Image {img_path}: {e}")

if sheet:
    save_sheet_with_lod(sheet, sheet_idx, current_sheet_size)

# ==========================================
# TREE PROCESSING & SAVING (OPTIMIZED)
# ==========================================

# 1. Assign 'gi' (Global Index) to the original sprite objects 
#    We do this BEFORE converting the tree to IDs, while we still have paths.
global_index_counter = 0

def assign_gi_and_filter(node):
    global global_index_counter
    # We filter and assign 'gi' at the same time
    
    # Process 'ai' (Active Images)
    valid_ai = []
    for path in node['ai']:
        if path in sprite_data:
            sprite_data[path]['gi'] = global_index_counter
            global_index_counter += 1
            valid_ai.append(path)
    node['ai'] = valid_ai
            
    # Process 'oi' (Other Images)
    valid_oi = []
    for path in node['oi']:
        if path in sprite_data:
            sprite_data[path]['gi'] = global_index_counter
            global_index_counter += 1
            valid_oi.append(path)
    node['oi'] = valid_oi

    for child in node['children']:
        assign_gi_and_filter(child)

assign_gi_and_filter(root)

# 2. Create the flat "Database" of all sprite objects
image_database_list = list(sprite_data.values())

# 3. Create a lookup map: Image Path -> ID (Integer)
path_to_id = { item['path']: i for i, item in enumerate(image_database_list) }

# 4. Inject IDs into the tree instead of full objects (NORMALIZATION)
def replace_images_with_ids(node):
    # 'ai' and 'oi' will now store Integers (0, 1, 2) instead of full Objects
    node['ai'] = [path_to_id[p] for p in node['ai'] if p in path_to_id]
    node['oi'] = [path_to_id[p] for p in node['oi'] if p in path_to_id]
    
    for child in node['children']:
        replace_images_with_ids(child)

replace_images_with_ids(root)

sprite_config = {
    'spritesheet_size': DEFAULTS['SPRITESHEET_SIZE'],
    'stack_spacing': DEFAULTS['STACK_SPACING'],
    'stack_dim_opacity': DEFAULTS['STACK_DIM_OPACITY'],
    'seed': DEFAULTS['SEED'],
    'loadingscreen_img_increment': DEFAULTS['LOADINGSCREEN_IMG_INCREMENT'],
    'ordered_grid_layout': DEFAULTS['ORDERED_GRID_LAYOUT'],
    'rotation_speed': DEFAULTS['ROTATION_SPEED'],
    'random_textdiv_position': DEFAULTS['RANDOM_TEXTDIV_POSITION'],
    'random_zoom': DEFAULTS['RANDOM_ZOOM'],
    'zoom_value': DEFAULTS['ZOOM_VALUE'],
    'quickload_threshold': DEFAULTS['QUICKLOAD_THRESHOLD'],
    'max_labels': DEFAULTS['MAX_LABELS'],
    'screen_buffer': DEFAULTS['SCREEN_BUFFER'],
    'colored_html_dots': DEFAULTS['COLORED_HTML_DOTS'],
    'breadcrumb_html_dots': DEFAULTS['BREADCRUMB_HTML_DOTS'],
    'show_nav_accessories': DEFAULTS['SHOW_NAV_ACCESSORIES'],
    'submenu_close_delay': DEFAULTS['SUBMENU_CLOSE_DELAY']
}

# 5. Save BOTH the tree (lightweight) and the database (heavy)
# with open('data.json', 'w') as f:
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump({
        'tree': root, 
        'database': image_database_list, 
        'sprite_config': sprite_config
    }, f, indent=None) # indent=None makes the file significantly smaller

# ==========================================
# HTML GENERATION
# ==========================================


#with open('index.html', 'w') as f:
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(f'''<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="styles.css">

<!-- <script src="https://unpkg.com/stats.js@0.17.0/build/stats.min.js"></script> -->

<meta charset="utf-8">

            <style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ 
    background: black; 
    color: white; 
    font-family: monospace; 
    font-size: var(--font-ui, 11px);
    display: flex;
    height: 100vh;
    overflow: hidden;
}}

#tree {{
    position: fixed;
    min-width: 280px;
    width: max-content;
    max-height: 80vh;
    overflow-y: auto;
    padding: 10px;
    display: flex;
    flex-direction: column;
    overflow-x: hidden;
    z-index: 1000;
    background: rgba(0,0,0,0.85);
    border: 1px solid #333;
    cursor: grab;
}}

#tree-content {{
    flex: 1;
    overflow-y: auto;
}}
#tree-search {{
    width: 60%;
    padding: 4px 6px;
    margin-bottom: 6px;
    background: rgba(0,0,0,0);
    color: white;
    border: none;
    font-family: monospace;
    font-size: var(--font-ui, 11px);
    outline: none;
}}

#content {{ 
    flex: 1; 
    display: flex;
    flex-wrap: wrap;
    overflow: hidden;
            
}}
.tree-item {{ white-space: pre; }}
.tree-link {{ cursor: pointer; color: white; user-select: none; }}
.tree-caret:hover, .tree-name:hover {{ background: #222; }}
.content-div {{
    border-left: 1px solid #333;
    border-bottom: 1px solid #333;

    box-sizing: border-box;
    position: relative;
    overflow: hidden;
}}
.div-label {{
    position: absolute;
    top: 5px;
    left: 5px;
    background: black;
    padding: 2px 5px;
    z-index: 100;
}}
.text-content {{
    padding: 20px;
    overflow-y: auto;
    white-space: pre-wrap;
}}
#label-container {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    overflow: hidden;
    z-index: 10;
}}
.stack-label {{
    position: absolute;
    top: 0;
    left: 0;
    will-change: transform;
    pointer-events: none;
    cursor: pointer;
    color: white;
    font-family: monospace;
    font-size: var(--font-ui, 11px);
    user-select: none;
    background: black;
    border-radius: 4px;
    line-height: 1.6;
    white-space: nowrap;
}}
.stack-label span {{ pointer-events: auto; }}
.stack-label > span[data-path]:hover {{ background: #222; }}
.stack-label .nav-deco {{ color: #666; font-size: var(--font-dots-md, 9px); }}
.stack-label .nav-count {{ color: white; margin-left: 2px; }}
.nav-ancestor-label {{ opacity: 0.7; }}
.nav-wire-svg {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 9; shape-rendering: crispEdges; }}
.nav-wire-svg path {{ fill: none; stroke: white; stroke-width: 1; }}
.nav-wire-svg .nav-wire-path {{ stroke-width: 5; }}
.nav-wire-svg .nav-wire-path-ancestor {{ stroke: rgba(255,255,255,0.5); stroke-width: 5; }}
.nav-wire-svg .nav-wire-path-dim {{ stroke: rgba(255,255,255,0.2); }}
.wire-arrow line {{ stroke: white; stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; }}
.wire-arrow-dim line {{ stroke: rgba(255,255,255,0.3); stroke-width: 1; }}
.dot-sm {{ font-size: var(--font-dots-sm, 7px); }}
.dot-md {{ font-size: var(--font-dots-md, 9px); }}
canvas {{ display: block; width: 100%; height: 100%; }}
</style>

</head>
<body>
<div id="tree">
    <input id="tree-search" type="text" placeholder="search..." />
    <div id="tree-content"></div>
</div>
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
import {{ BufferGeometryUtils }} from 'three/addons/utils/BufferGeometryUtils.js';

(() => {{
    const tree = document.getElementById('tree');
    const treeContent = document.getElementById('tree-content');
    const searchInput = document.getElementById('tree-search');
    let dragging = false, ox = 0, oy = 0, tabIndex = -1, visibleMatches = [];

    tree.style.left = Math.floor(Math.random() * Math.max(0, innerWidth - 300)) + 'px';
    tree.style.top = Math.floor(Math.random() * Math.max(0, innerHeight - 400)) + 'px';

    tree.addEventListener('mousedown', (e) => {{
        if (e.target.closest('.tree-link, #tree-search')) return;
        dragging = true; ox = e.clientX - tree.offsetLeft; oy = e.clientY - tree.offsetTop;
        tree.style.cursor = 'grabbing'; document.body.style.userSelect = 'none';
    }});
    document.addEventListener('mousemove', (e) => {{ if (dragging) {{ tree.style.left = (e.clientX - ox) + 'px'; tree.style.top = (e.clientY - oy) + 'px'; }} }});
    document.addEventListener('mouseup', () => {{ if (dragging) {{ dragging = false; tree.style.cursor = 'grab'; document.body.style.userSelect = ''; }} }});

    function clearSearch() {{
        visibleMatches.forEach(l => l.style.background = '');
        searchInput.value = ''; tabIndex = -1;
        treeContent.querySelectorAll('.tree-item').forEach(el => el.style.display = '');
        treeContent.querySelectorAll('.tree-children').forEach(el => el.style.display = 'none');
        updateTreeState(true);
    }}

    function highlightMatch(idx) {{
        visibleMatches.forEach(l => l.style.background = '');
        if (idx >= 0 && idx < visibleMatches.length) {{
            visibleMatches[idx].style.background = '#333';
            const item = visibleMatches[idx].closest('.tree-item');
            if (item) {{
                const top = item.offsetTop, bot = top + item.offsetHeight;
                if (bot > treeContent.scrollTop + treeContent.clientHeight) treeContent.scrollTop = bot - treeContent.clientHeight;
                else if (top < treeContent.scrollTop) treeContent.scrollTop = top;
            }}
        }}
    }}

    function collectVisible() {{
        visibleMatches = Array.from(treeContent.querySelectorAll('.tree-link')).filter(link => {{
            if (link.style.textDecoration === 'line-through') return false;
            let el = link.closest('.tree-item');
            while (el && el !== treeContent) {{ if (el.style.display === 'none') return false; el = el.parentElement; }}
            return true;
        }});
    }}

    searchInput.addEventListener('input', () => {{
        const q = searchInput.value.toLowerCase().trim();
        tabIndex = -1;
        if (!q) {{ clearSearch(); return; }}
        treeContent.querySelectorAll('.tree-item').forEach(el => el.style.display = 'none');
        treeContent.querySelectorAll('.tree-children').forEach(el => el.style.display = 'none');
        treeContent.querySelectorAll('.tree-link').forEach(link => {{
            if (!link.textContent.toLowerCase().includes(q) && !(link.dataset.keywords && link.dataset.keywords.includes(q))) return;
            const item = link.closest('.tree-item');
            if (!item) return;
            item.style.display = '';
            const sib = item.nextElementSibling;
            if (sib && sib.classList.contains('tree-children')) {{
                sib.querySelectorAll('.tree-item').forEach(el => el.style.display = '');
                sib.querySelectorAll('.tree-children').forEach(el => el.style.display = 'none');
            }}
            let p = item.parentElement;
            while (p && p !== treeContent) {{
                if (p.classList.contains('tree-children')) p.style.display = 'block';
                if (p.classList.contains('tree-item')) p.style.display = '';
                p = p.parentElement;
            }}
        }});
        collectVisible();
        updateTreeState();
    }});

    searchInput.addEventListener('mousedown', (e) => e.stopPropagation());
    searchInput.addEventListener('keydown', (e) => {{
        if (e.key === 'Tab') {{
            e.preventDefault(); collectVisible();
            if (!visibleMatches.length) return;
            tabIndex = e.shiftKey ? (tabIndex <= 0 ? visibleMatches.length - 1 : tabIndex - 1) : (tabIndex + 1) % visibleMatches.length;
            highlightMatch(tabIndex);
        }} else if (e.key === 'Enter') {{
            e.preventDefault();
            const target = (tabIndex >= 0 && tabIndex < visibleMatches.length) ? visibleMatches[tabIndex] : (collectVisible(), visibleMatches[0]);
            const name = target?.querySelector('.tree-name');
            if (name) name.click();
            clearSearch();
        }} else if (e.key === 'Escape') {{ clearSearch(); searchInput.blur(); }}
    }});
    document.addEventListener('keydown', (e) => {{ if (e.key === 'Escape' && document.activeElement !== searchInput) clearSearch(); }});
}})();

const loader = document.createElement('div');
loader.id = 'loader';
loader.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:black;color:white;display:flex;align-items:center;justify-content:center;z-index:99999;font-family:monospace;';
loader.textContent = 'initializing...';
document.body.appendChild(loader);

            
const GRID_COLS = window.innerWidth > 768 ? 20 : 1;
const GRID_ROWS = window.innerWidth > 768 ? 1 : 20;
const GRID_TOTAL = GRID_COLS * GRID_ROWS;

const _gridOrder = Array.from({{length: GRID_TOTAL}}, (_, i) => i);
(function shuffle(a) {{
    let s = 9301;
    for (let i = a.length - 1; i > 0; i--) {{
        s = (s * 16807 + 1) & 0x7fffffff;
        const j = s % (i + 1);
        [a[i], a[j]] = [a[j], a[i]];
    }}
}})(_gridOrder);

let progress = {{ss: 0, ssTotal: 0, stacks: 0, stacksTotal: 0, imgs: 0, imgsTotal: 0}};

function makeGrid(percent) {{
    const filled = Math.floor((percent / 100) * GRID_TOTAL);
    const active = new Set(_gridOrder.slice(0, filled));
    let rows = '';
    for (let r = 0; r < GRID_ROWS; r++) {{
        let row = '';
        for (let c = 0; c < GRID_COLS; c++) {{
            row += active.has(r * GRID_COLS + c) ? '\u00B7' : '\u00A0';
        }}
        rows += row + '\\n';
    }}
    return rows;
}}

function updateLoader() {{
    const l = document.getElementById('loader');
    if (!l) return;
    
    const ssPercent = progress.ssTotal > 0 ? Math.floor((progress.ss / progress.ssTotal) * 100) : 0;
    const stacksPercent = progress.stacksTotal > 0 ? Math.floor((progress.stacks / progress.stacksTotal) * 100) : 0;
    const imgsPercent = progress.imgsTotal > 0 ? Math.floor((progress.imgs / progress.imgsTotal) * 100) : 0;
    
    const linkStyle = 'color:white;text-decoration:underline;display:block;text-align:right;line-height:1.8;';

    l.innerHTML = `<div style="font-family:monospace;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:24px;">
            <div>
                <div style="margin-bottom:4px;">archigrad.io</div>
                <div>office for architecture and computation</div>
            </div>
            <div style="text-align:right;">
                <a href="https://github.com/archiGrad" target="_blank" style="${{linkStyle}}">github</a>
                <a href="#" style="${{linkStyle}}">whatsapp</a>
                <a href="#" style="${{linkStyle}}">line</a>
                <a href="mailto:putteneersjoris@gmail.com" style="${{linkStyle}}">email</a>
            </div>
        </div>
        <div style="display:flex;gap:24px;">
            <div style="flex:1;">
                <div style="margin-bottom:6px;">spritesheets:<br>${{progress.ss}}/${{progress.ssTotal}}</div>
                <pre style="margin:0;font-size:var(--font-loading-grid, 10px);line-height:1.2;letter-spacing:2px;">${{makeGrid(ssPercent)}}</pre>
                <div style="margin-top:4px;">${{ssPercent}}%</div>
            </div>
            <div style="flex:1;">
                <div style="margin-bottom:6px;">stacks:<br>${{progress.stacks}}/${{progress.stacksTotal}}</div>
                <pre style="margin:0;font-size:var(--font-loading-grid, 10px);line-height:1.2;letter-spacing:2px;">${{makeGrid(stacksPercent)}}</pre>
                <div style="margin-top:4px;">${{stacksPercent}}%</div>
            </div>
            <div style="flex:1;">
                <div style="margin-bottom:6px;">images:<br>${{progress.imgs}}/${{progress.imgsTotal}}</div>
                <pre style="margin:0;font-size:var(--font-loading-grid, 10px);line-height:1.2;letter-spacing:2px;">${{makeGrid(imgsPercent)}}</pre>
                <div style="margin-top:4px;">${{imgsPercent}}%</div>
            </div>
        </div>
    </div>`;
}}

async function updateLoaderAsync() {{
    updateLoader();
    await new Promise(r => requestAnimationFrame(r));
}}

let dataTree;
let spriteConfig;
let activeScenes = [];
const textureCache = {{}};
const pendingLoads = {{}};
const stackMaterialCache = {{}};
const lodAvailable = {{}};
const LOD_COUNT = 3;

function ssBase(ssArray) {{ return ssArray[0].replace('_lod0', ''); }}

function seededRandom(seed) {{
    let state = seed;
    state = (state * 1664525 + 1013904223) % 4294967296;
    return state / 4294967296;
}}

function seededColorFromPath(path) {{
    const hash = path.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
    let state = hash * spriteConfig.seed;
    function next() {{ state = (state * 1664525 + 1013904223) % 4294967296; return state / 4294967296; }}
    return `hsl(${{Math.floor(next() * 360)}},${{60 + Math.floor(next() * 30)}}%,${{50 + Math.floor(next() * 20)}}%)`;
}}

function buildHtmlDots(atArray, sizeClass) {{
    if (!atArray || atArray.length === 0) return '';
    return atArray.map(p => {{
        const c = spriteConfig.colored_html_dots ? seededColorFromPath(p) : '#fff';
        return `<span class="${{sizeClass}}" style="color:${{c}};vertical-align:middle;margin-left:1px;">●</span>`;
    }}).join('');
}}

function dotSpan(color, cls) {{
    return `<span class="${{cls}}" style="color:${{color}};vertical-align:middle;margin-left:1px;">●</span>`;
}}

function navDeco(node, cls, showHtmlDots) {{
    if (!node) return '';
    let d = '';
    if (node.na) d += ' ' + dotSpan('#44f', cls);
    if (node.sa) d += ' ' + dotSpan('#4f4', cls);
    if (showHtmlDots !== false && node.at && node.at.length > 0) d += ' ' + buildHtmlDots(node.at, cls);
    if (node._dc > 0) d += `<span class="nav-count">(${{node._dc}})</span>`;
    return d;
}}

function breadcrumbHtml(path, activePath) {{
    const parts = path.split('/');
    return parts.map((part, idx) => {{
        const partPath = parts.slice(0, idx + 1).join('/');
        const color = (activePath && partPath === activePath) ? '#44f' : 'white';
        const pNode = findNodeByPath(dataTree, partPath);
        const acc = spriteConfig.show_nav_accessories;
        const deco = acc ? navDeco(pNode, 'dot-md', spriteConfig.breadcrumb_html_dots) : '';
        return `<span style="color:${{color}};cursor:pointer" data-path="${{partPath}}">${{part}}${{deco}}</span>`;
    }}).join(' <span style="color:white">&gt;</span> ');
}}

function assembleHtmlParts(parts, paths) {{
    const total = parts.length;
    return parts.map((part, i) => {{
        const dot = (spriteConfig.show_nav_accessories && spriteConfig.colored_html_dots) ? `<span style="color:${{seededColorFromPath(paths[i])}};margin-left:4px;">●</span>` : '';
        const pageLabel = total > 1 ? `<div style="font-family:monospace;font-size:var(--font-page-index, 10px);color:#666;margin-top:12px;">${{i+1}}/${{total}}${{dot}}</div>` : '';
        const separator = i < total - 1 ? '<hr style="border:none;border-top:1px solid #333;margin:20px -20px;padding:0;">' : '';
        return part + pageLabel + separator;
    }}).join('');
}}


async function loadSpritesheet(path) {{
    if (textureCache[path]) return textureCache[path];
    if (pendingLoads[path]) return pendingLoads[path];
    pendingLoads[path] = (async () => {{
        const resp = await fetch(path);
        const blob = await resp.blob();
        const bitmap = await createImageBitmap(blob, {{ imageOrientation: 'flipY' }});
        const texture = new THREE.CanvasTexture(bitmap);
        texture.flipY = false;
        texture.minFilter = THREE.NearestFilter;
        texture.magFilter = THREE.NearestFilter;
        texture.generateMipmaps = false;
        textureCache[path] = texture;
        delete pendingLoads[path];
        const base = path.replace(/_lod\\d/, '');
        if (!lodAvailable[base]) lodAvailable[base] = {{}};
        const lodMatch = path.match(/_lod(\\d)/);
        if (lodMatch) lodAvailable[base][parseInt(lodMatch[1])] = path;
        if (lodMatch && lodMatch[1] === '0') progress.ss++;
        updateLoader();
        return texture;
    }})();
    return pendingLoads[path];
}}

function getBestLod(ssArray, maxLod) {{
    const base = ssArray[0].replace(/_lod\\d/, '');
    const avail = lodAvailable[base] || {{}};
    for (let l = maxLod; l < LOD_COUNT; l++) {{
        if (avail[l] && textureCache[avail[l]]) return textureCache[avail[l]];
    }}
    for (let l = maxLod - 1; l >= 0; l--) {{
        if (avail[l] && textureCache[avail[l]]) return textureCache[avail[l]];
    }}
    return null;
}}

function getStackMaterial(ssArray, stackName) {{
    const key = `${{ssBase(ssArray)}}::${{stackName}}`;
    if (!stackMaterialCache[key]) {{
        const tex = getBestLod(ssArray, LOD_COUNT - 1) || textureCache[ssArray[LOD_COUNT - 1]];
        stackMaterialCache[key] = new THREE.MeshBasicMaterial({{
            map: tex,
            side: THREE.DoubleSide,
            transparent: true,
            alphaTest: 0.1,
            opacity: 1
        }});
        stackMaterialCache[key]._ssArray = ssArray;
    }}
    return stackMaterialCache[key];
}}





fetch('data.json')
    .then(r => r.json())
    .then(async d => {{
        const db = d.database;
        dataTree = d.tree;
        spriteConfig = d.sprite_config;

        function hydrate(node) {{
            if (node.ai) node.ai = node.ai.map(id => db[id]);
            if (node.oi) node.oi = node.oi.map(id => db[id]);
            if (node.children) node.children.forEach(hydrate);
        }}
        hydrate(dataTree);
        precomputeCounts(dataTree);

        buildTree(dataTree, document.getElementById('tree-content'));
        progress = {{ss: 0, ssTotal: 0, stacks: 0, stacksTotal: 0, imgs: 0, imgsTotal: 0}};

        const params = new URLSearchParams(window.location.search);
        const path = params.get('path');

        const targetNode = path ? findNodeByPath(dataTree, path) : dataTree;
        
        await renderContent(targetNode || dataTree);
        
        isInitialLoad = false;
        const loaderEl = document.getElementById('loader');
        if (loaderEl) loaderEl.remove();

            const hash = window.location.hash.slice(2);

        if (hash) {{

            const node = findNodeByPath(dataTree, hash);

            if (node) await renderContent(node);

        }}

    }});











window.addEventListener('hashchange', () => {{
    const hash = window.location.hash.slice(2);
    const node = hash ? findNodeByPath(dataTree, hash) : dataTree;
    if (node) renderContent(node);
}});

document.addEventListener('mousemove', (e) => {{
    window._lastEdgeNavX = e.clientX;
    window._lastEdgeNavY = e.clientY;
}});


function precomputeCounts(node) {{
    let count = 0;
    if (node.children) {{
        for (const child of node.children) {{
            count += 1 + precomputeCounts(child);
        }}
    }}
    node._dc = count;
    return count;
}}

function buildTree(node, container, depth = 0, isLast = true, prefix = '') {{
    const connector = '';
    const item = document.createElement('div');
    item.className = 'tree-item';
    item.innerHTML = prefix + connector;
    const link = document.createElement('span');
    link.className = 'tree-link';
    
    const hasChildren = node.children && node.children.length > 0;
    const deco = navDeco(node, 'dot-sm');

    if (hasChildren) {{
        const caret = document.createElement('span');
        caret.className = 'tree-caret';
        caret.textContent = '>';
        caret.onclick = (e) => {{
            e.stopPropagation();
            const cc = link._childContainer;
            if (cc) cc.style.display = cc.style.display === 'none' ? 'block' : 'none';
            updateTreeState();
        }};
        link.appendChild(caret);
        link.appendChild(document.createTextNode(' '));
    }}

    const nameSpan = document.createElement('span');
    nameSpan.className = 'tree-name';
    nameSpan.innerHTML = node.name + deco;
    link.appendChild(nameSpan);
    link.dataset.path = node.path;
    if (node.sk && node.sk.length) link.dataset.keywords = node.sk.join(',').toLowerCase();
    
    if (node.hid) {{
        link.style.textDecoration = 'line-through';
        link.style.color = '#666';
        link.style.cursor = 'not-allowed';
        link.title = 'Hidden';
    }} else {{
        nameSpan.onclick = (e) => {{
            e.stopPropagation();
            if (!currentNode || currentNode.path !== node.path) {{
                renderContent(node);
                updateTreeState(true);
            }}
        }};
    }}
    
    item.appendChild(link);
    container.appendChild(item);
    
    if (hasChildren) {{
        const childContainer = document.createElement('div');
        childContainer.className = 'tree-children';
        childContainer.style.display = 'none';
        link._childContainer = childContainer;
        const newPrefix = prefix + '  ';
        node.children.forEach((child, i) => {{
            buildTree(child, childContainer, depth + 1, i === node.children.length - 1, newPrefix);
        }});
        container.appendChild(childContainer);
    }}
}}

function updateTreeState(expand) {{
    if (!currentNode) {{
        document.querySelectorAll('.tree-caret').forEach(caret => {{
            const link = caret.closest('.tree-link');
            const cc = link?._childContainer;
            if (cc) caret.textContent = cc.style.display === 'none' ? '>' : 'v';
        }});
        return;
    }}
    const ancestorSet = new Set(), descendantSet = new Set();
    const parts = currentNode.path.split('/');
    for (let i = 1; i < parts.length; i++) ancestorSet.add(parts.slice(0, i).join('/'));
    (function collect(n) {{ n.children.forEach(c => {{ descendantSet.add(c.path); collect(c); }}); }})(currentNode);

    document.querySelectorAll('.tree-link').forEach(link => {{
        const p = link.dataset.path;
        if (expand && ancestorSet.has(p)) {{
            const cc = link._childContainer;
            if (cc) cc.style.display = 'block';
        }}
        let color;
        if (link.style.textDecoration === 'line-through') color = '#666';
        else if (p === currentNode.path) color = '#44f';
        else if (ancestorSet.has(p) || descendantSet.has(p)) color = 'white';
        else color = '#444';
        link.style.color = color;
        const countSpan = link.querySelector('.tree-count');
        if (countSpan) countSpan.style.color = color;
    }});
    document.querySelectorAll('.tree-caret').forEach(caret => {{
        const link = caret.closest('.tree-link');
        const cc = link?._childContainer;
        if (cc) caret.textContent = cc.style.display === 'none' ? '>' : 'v';
    }});
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
        sceneData.renderer.dispose();
        if (sceneData.renderer.domElement.parentNode) {{
            sceneData.renderer.domElement.parentNode.removeChild(sceneData.renderer.domElement);
        }}
    }}
    if (sceneData.scene) {{
        sceneData.scene.traverse((object) => {{
            if (object.geometry) object.geometry.dispose();
        }});
        sceneData.scene.clear();
    }}
}}

async function createThreeScene(container, images, node) {{
    const scene = new THREE.Scene();
    const grouped = {{}};
    const stackGroups = {{}};

    const SPRITESHEET_SIZE = spriteConfig.spritesheet_size;
    const STACK_SPACING = spriteConfig.stack_spacing;
    const STACK_DIM_OPACITY = spriteConfig.stack_dim_opacity;
    const SEED = spriteConfig.seed;
    const ORDERED_GRID_LAYOUT = spriteConfig.ordered_grid_layout;
    const ROTATION_SPEED = spriteConfig.rotation_speed;

    images.forEach(imgData => {{
        const parts = imgData.path.split('/');
        const folder = parts.slice(0, -1).join('/') || 'root';
        if (!grouped[folder]) grouped[folder] = [];
        grouped[folder].push(imgData);
    }});
    
    const folders = Object.keys(grouped);
    folders.forEach(folder => {{ grouped[folder].sort((a, b) => a.gi - b.gi); }});
   
    progress.imgsTotal += images.length;
    progress.stacksTotal += folders.length;
    const uniqueSS = new Set();
    images.forEach(i => i.ss.forEach(p => uniqueSS.add(p)));
    const uniqueSSBase = new Set();
    images.forEach(i => {{ if (i.ss[0]) uniqueSSBase.add(i.ss[0]); }});
    progress.ssTotal += uniqueSSBase.size;
    uniqueSSBase.forEach(ss => {{ if (textureCache[ss]) progress.ss++; }});
    updateLoader();
 
    const baseGeometry = new THREE.PlaneGeometry(1, 1);
    
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
            if (n.hid) return;
            const childFolders = folders.filter(f => f.startsWith(n.path + '/') || f === n.path);
            if (n.grid_layout && n.ai.length > 0 && childFolders.length > 0) {{
                const [gCols, gRows] = ORDERED_GRID_LAYOUT ? n.grid_layout.split('x').map(Number) : [1, 1];
                gridGroups.push({{ folders: childFolders, cols: gCols, rows: gRows, path: n.path }});
                childFolders.forEach(f => processedFolders.add(f));
            }} else if (n.children.length > 0) {{
                n.children.forEach(child => collectGridChildren(child));
            }} else if (childFolders.length > 0) {{
                gridGroups.push({{ folders: childFolders, cols: 1, rows: 1, path: n.path }});
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
                                if (!isOccupied(dx, dy, w, h)) return {{ x: dx, y: dy }};
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
    
    const calculateBounds = (x, z) => {{
        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x);
        minZ = Math.min(minZ, z);
        maxZ = Math.max(maxZ, z);
    }};
    const folderPositions = {{}};
    
    // --- 2. Iterate to Calculate Scene Size ---
    if (node.grid_layout) {{
        folders.forEach((folder, stackIdx) => {{
            const row = Math.floor(stackIdx / cols);
            const col = stackIdx % cols;
            const x = col * spacing - offsetX;
            const z = row * spacing - offsetZ;
            folderPositions[folder] = {{x, z}};
            calculateBounds(x, z);
        }});
    }} else if (gridGroups && gridGroups.length > 0) {{
        gridGroups.forEach(group => {{
            group.folders.forEach((folder, localIdx) => {{
                const row = Math.floor(localIdx / group.cols);
                const col = localIdx % group.cols;
                const x = (group.gridX + col) * spacing - offsetX;
                const z = (group.gridY + row) * spacing - offsetZ;
                folderPositions[folder] = {{x, z}};
                calculateBounds(x, z);
            }});
        }});
    }} else {{
        folders.forEach((folder, stackIdx) => {{
            const row = Math.floor(stackIdx / cols);
            const col = stackIdx % cols;
            const x = col * spacing - offsetX;
            const z = row * spacing - offsetZ;
            folderPositions[folder] = {{x, z}};
            calculateBounds(x, z);
        }});
    }}

    folders.forEach((folder, stackIdx) => {{
        if (folderPositions[folder]) return;
        const col = stackIdx % (cols || 1);
        const row = Math.floor(stackIdx / (cols || 1));
        const x = col * spacing - (offsetX || 0);
        const z = row * spacing - (offsetZ || 0);
        folderPositions[folder] = {{x, z}};
        calculateBounds(x, z);
    }});

    const meshMaxSize = 1.5 * 1.5;
    const geomWidth = maxX - minX + meshMaxSize;
    const geomDepth = maxZ - minZ + meshMaxSize;
    
    // Add margin (was 15 previously)
    const maxSceneDim = Math.max(geomWidth, geomDepth) + 5;

    // Calculate Aspect Ratio from the Container
    const aspectRatio = container.clientWidth / container.clientHeight;

    // FIT LOGIC: 
    // If Portrait (aspect < 1), div is narrow -> Zoom out (increase frustum) to fit width.
    // If Landscape (aspect >= 1), div is wide -> Height is the limiter, use maxSceneDim.
    const fitFrustumSize = aspectRatio < 1 ? maxSceneDim / aspectRatio : maxSceneDim;

    // ZOOM LOGIC:
    const RANDOM_ZOOM = spriteConfig.random_zoom;
    const GLOBAL_ZOOM_VALUE = spriteConfig.zoom_value;
    const nodeZoom = (node && node.mzm != null) ? node.mzm : null;

    let randomZoom;
    if (nodeZoom != null) {{
        randomZoom = nodeZoom;
    }} else if (!RANDOM_ZOOM) {{
        randomZoom = GLOBAL_ZOOM_VALUE;
    }} else {{
        const seed = images.map(img => img.gi).reduce((a, b) => a + b, 0);
        const rand = seededRandom(seed * SEED);
        if (rand < 0.33) {{
            randomZoom = 0.1;
        }} else if (rand < 0.66) {{
            randomZoom = 0.4;
        }} else {{
            randomZoom = 1.0;
        }}
    }}
    
    console.log(`DEBUG: Zoom=${{randomZoom.toFixed(2)}}, RandomMode=${{RANDOM_ZOOM}}, NodeOverride=${{nodeZoom}}`);



    // Apply the random multiplier to the perfect fit
    const frustumSize = fitFrustumSize * randomZoom;

    // --- 4. Create Camera ---
    const camera = new THREE.OrthographicCamera(
        frustumSize * aspectRatio / -2,
        frustumSize * aspectRatio / 2,
        frustumSize / 2,
        frustumSize / -2,
        0.1,
        1000
    );
    
    const renderer = new THREE.WebGLRenderer({{ 
        alpha: true, 
        antialias: true,
        powerPreference: 'high-performance'
    }});
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000);
    container.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enablePan = true;

    const navButtons = document.createElement('div');
    navButtons.style.cssText = 'position:absolute;top:5px;right:5px;display:flex;gap:5px;z-index:100';
    const createButton = () => {{
        const btn = document.createElement('button');
        btn.style.cssText = 'color:#fff;border:none;padding:0.3em;cursor:pointer;border-radius:50%;font-size:var(--font-ui, 11px)';
        return btn;
    }};
    const topBtn = createButton(); const rightBtn = createButton();
    const bottomBtn = createButton(); const leftBtn = createButton();
    navButtons.append(topBtn, rightBtn, bottomBtn, leftBtn);
    container.appendChild(navButtons);

   
    let maxStackHeight = 0;
    folders.forEach(folder => {{
        // Find the specific node for this folder to check for custom spacing
        const folderNode = findNodeByPath(dataTree, folder);
        const localSpacing = (folderNode && folderNode.msp != null) ? folderNode.msp : STACK_SPACING;
        
        maxStackHeight = Math.max(maxStackHeight, grouped[folder].length * localSpacing);
    }});
    const midHeight = maxStackHeight / 2;

    topBtn.onclick = () => {{ camera.position.set(0.01, midHeight + 15, 0); controls.target.set(0, midHeight, 0); controls.update(); }};
    rightBtn.onclick = () => {{ camera.position.set(15, midHeight + 0.3, 0.0); controls.target.set(0, midHeight, 0); controls.update(); }};
    bottomBtn.onclick = () => {{ camera.position.set(0.01, midHeight - 15, 0); controls.target.set(0, midHeight, 0); controls.update(); }};
    leftBtn.onclick = () => {{ camera.position.set(-15, midHeight + 0.3, 0.0); controls.target.set(0, midHeight, 0); controls.update(); }};

    camera.position.set(10, 10 + midHeight, 10);
    controls.target.set(0, midHeight, 0);

    const labelContainer = document.createElement('div');
    labelContainer.id = 'label-container';
    container.appendChild(labelContainer);

    const wireSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    wireSvg.classList.add('nav-wire-svg');
    wireSvg.setAttribute('width', '100%');
    wireSvg.setAttribute('height', '100%');
    wireSvg.style.overflow = 'visible';
    container.appendChild(wireSvg);
    function makeSvgPath(cls) {{ const p = document.createElementNS('http://www.w3.org/2000/svg', 'path'); p.classList.add(cls); wireSvg.appendChild(p); return p; }}
    const wirePathDim = makeSvgPath('nav-wire-path-dim');
    const wirePathAncestor = makeSvgPath('nav-wire-path-ancestor');
    const wirePath = makeSvgPath('nav-wire-path');
    const wireArrowG = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    wireSvg.appendChild(wireArrowG);
    let mouseX = 0, mouseY = 0, mouseIsDown = false;
    document.addEventListener('pointerdown', (e) => {{ if (e.button === 0 || e.button === 1) mouseIsDown = true; }});
    document.addEventListener('pointerup', (e) => {{ if (e.button === 0 || e.button === 1) mouseIsDown = false; }});
    container.addEventListener('mousemove', (e) => {{
        const rect = container.getBoundingClientRect();
        mouseX = e.clientX - rect.left;
        mouseY = e.clientY - rect.top;
    }});

 
    const toggleBtn = document.createElement('button');
    toggleBtn.style.cssText = 'position:absolute;bottom:5px;left:5px;background:#44f;border:none;width:0.7em;height:0.7em;border-radius:50%;cursor:pointer;padding:0;z-index:100;font-size:var(--font-ui, 11px)';
    let labelsVisible = true;
    toggleBtn.onclick = () => {{
        labelsVisible = !labelsVisible;
        labelContainer.style.display = labelsVisible ? 'block' : 'none';
        wireSvg.style.display = labelsVisible ? '' : 'none';
        toggleBtn.style.background = labelsVisible ? '#44f' : '#f44';
    }};
    container.appendChild(toggleBtn);

    const countDiv = document.createElement('div');
    countDiv.style.cssText = 'position:absolute;bottom:5px;right:5px;color:white;font-family:monospace;';
    container.appendChild(countDiv);

    let loadedStacks = 0;
    let loadedImages = 0;
    const totalStacks = folders.length;
    const totalImages = images.length;

    const updateCount = () => {{
        const downColor = currentNode && currentNode.children.length > 0 ? '#ffffff' : '#000';
        const gridInfo = node.grid_layout ? ` [${{node.grid_layout}}]` : '';
        countDiv.innerHTML = `zoom: ${{randomZoom.toFixed(2)}}${{gridInfo}} | ${{loadedStacks + 1}}/${{totalStacks}} stacks | ${{loadedImages}}/${{totalImages}} images`;
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
            if (currentNode && currentNode.children.length > 0) renderContent(currentNode.children[0]);
        }}
    }});

    const stackLabels = [];
    let currentFocusedParent = null;
    let activeLabelPath = null;
    let activeGroupPath = null;
    function focusStackGroup(parentFolder) {{
        if (currentFocusedParent === parentFolder) {{
            unfocusAll();
            currentFocusedParent = null;
        }} else {{
            for (const [folder, data] of Object.entries(stackGroups)) {{
                const op = (folder.startsWith(parentFolder + '/') || folder === parentFolder) ? 1.0 : STACK_DIM_OPACITY;
                data.materials.forEach(m => m.opacity = op);
            }}
            stackLabels.forEach(sl => {{
                const match = sl.folderName.startsWith(parentFolder + '/') || sl.folderName === parentFolder;
                sl.element.style.opacity = match ? '1.0' : String(STACK_DIM_OPACITY);
            }});
            currentFocusedParent = parentFolder;
        }}
    }}
    function unfocusAll() {{
        for (const [folder, data] of Object.entries(stackGroups)) {{
            data.materials.forEach(m => m.opacity = 1.0);
        }}
        stackLabels.forEach(sl => sl.element.style.opacity = '1.0');
        currentFocusedParent = null;
    }}

    const loadingPromise = (async () => {{
        const allSSArrays = new Set();
        folders.forEach(folder => {{
            grouped[folder].forEach(img => allSSArrays.add(JSON.stringify(img.ss)));
        }});
        const uniqueSSArrays = [...allSSArrays].map(s => JSON.parse(s));
        
        const lod2Paths = uniqueSSArrays.map(ss => ss[LOD_COUNT - 1]);
        await Promise.all(lod2Paths.map(p => loadSpritesheet(p)));
        
        const groupLabelData = {{}};
        for (let stackIdx = 0; stackIdx < folders.length; stackIdx++) {{
            const folderName = folders[stackIdx];


            // --- NEW: Retrieve Custom Spacing for this specific stack ---
            const folderNode = findNodeByPath(dataTree, folderName);
            const localSpacing = (folderNode && folderNode.msp != null) ? folderNode.msp : STACK_SPACING;
            // ------------------------------------------------------------


            const stackImages = grouped[folderName];
            const pos = folderPositions[folderName];
            const xPos = pos.x;
            const zPos = pos.z;

            const stackGroup = new THREE.Group();
            const stackMaterials = new Set();
            const mergeBuckets = {{}};
            const animObjects = [];

            for (let i = 0; i < stackImages.length; i++) {{
                const imgData = stackImages[i];
                stackMaterials.add(getStackMaterial(imgData.ss, folderName));
                
                const aspect = imgData.w / imgData.h;
                const height = 1.5;
                const width = height * aspect;

                const y = i * localSpacing;
                const matrix = new THREE.Matrix4();
                const position = new THREE.Vector3(xPos, y, zPos);
                const rotation = new THREE.Euler(Math.PI / 2, Math.PI, Math.PI);
                const quaternion = new THREE.Quaternion().setFromEuler(rotation);
                const scale = new THREE.Vector3(width, height, 1);
                matrix.compose(position, quaternion, scale);
                
                const currentSpriteSize = imgData.sz; 
                const SPRITES_PER_ROW = Math.floor(SPRITESHEET_SIZE / currentSpriteSize);

                if (imgData.anim) {{
                    const mesh = new THREE.Mesh(baseGeometry.clone(), getStackMaterial(imgData.ss, folderName));
                    mesh.applyMatrix4(matrix);
                    
                    mesh.userData = {{ imgData: imgData, spritesheet: imgData.ss, spritesPerRow: SPRITES_PER_ROW }};
                    mesh.onBeforeRender = function() {{
                        const frame = Math.floor(Date.now() / this.userData.imgData.gd) % this.userData.imgData.fc;
                        const idx = this.userData.imgData.si + frame;
                        const rowLen = this.userData.spritesPerRow;
                        const sprite_col = idx % rowLen;
                        const sprite_row = Math.floor(idx / rowLen);
                        
                        const size = this.userData.imgData.sz;
                        const u_start = (sprite_col * size) / SPRITESHEET_SIZE;
                        const u_end = u_start + size / SPRITESHEET_SIZE;
                        const v_start = 1 - ((sprite_row + 1) * size) / SPRITESHEET_SIZE;
                        const v_end = 1 - (sprite_row * size ) / SPRITESHEET_SIZE;
                        
                        const uvs = this.geometry.attributes.uv;
                        uvs.setXY(0, u_start, v_end);
                        uvs.setXY(1, u_end, v_end);
                        uvs.setXY(2, u_start, v_start);
                        uvs.setXY(3, u_end, v_start);
                        uvs.needsUpdate = true;
                    }};
                    animObjects.push(mesh);
                }} else {{
                    const bKey = ssBase(imgData.ss);
                    if (!mergeBuckets[bKey]) mergeBuckets[bKey] = {{ geoms: [], ssArray: imgData.ss }};
                    
                    const geometry = baseGeometry.clone();
                    geometry.applyMatrix4(matrix);
                    
                    const idx = imgData.idx;
                    const sprite_col = idx % SPRITES_PER_ROW;
                    const sprite_row = Math.floor(idx / SPRITES_PER_ROW);
                    const u_start = (sprite_col * currentSpriteSize) / SPRITESHEET_SIZE;
                    const u_end = u_start + imgData.w / SPRITESHEET_SIZE;
                    const v_start = 1 - ((sprite_row + 1) * currentSpriteSize) / SPRITESHEET_SIZE;
                    const v_end = 1 - (sprite_row * currentSpriteSize) / SPRITESHEET_SIZE;
                    
                    const uvs = geometry.attributes.uv;
                    uvs.setXY(0, u_start, v_end);
                    uvs.setXY(1, u_end, v_end);
                    uvs.setXY(2, u_start, v_start);
                    uvs.setXY(3, u_end, v_start);
                    
                    mergeBuckets[bKey].geoms.push(geometry);
                }}
                loadedImages++;
                progress.imgs++;
            }}

            for (const [bKey, bucket] of Object.entries(mergeBuckets)) {{
                if (bucket.geoms.length > 0) {{
                    const mergedGeo = BufferGeometryUtils.mergeBufferGeometries(bucket.geoms);
                    const mat = getStackMaterial(bucket.ssArray, folderName);
                    const mesh = new THREE.Mesh(mergedGeo, mat);
                    stackGroup.add(mesh);
                    bucket.geoms.forEach(g => g.dispose());
                }}
            }}
            animObjects.forEach(obj => stackGroup.add(obj));
            scene.add(stackGroup);
            stackGroups[folderName] = {{ group: stackGroup, materials: stackMaterials }};

            updateCount();
            loadedStacks++;
            progress.stacks++;
            if (progress.stacks % 5 === 0) await updateLoaderAsync();


            // Collect group data for labels
            const topY = (stackImages.length - 1) * localSpacing;
            const scenePath = node.path || '';
            let relPath = '';
            if (folderName.startsWith(scenePath + '/')) {{
                relPath = folderName.slice(scenePath.length + 1);
            }} else if (scenePath === '') {{
                relPath = folderName;
            }}
            const groupKey = relPath.split('/').filter(p => p)[0] || folderName.split('/').pop();
            if (!groupLabelData[groupKey]) {{
                groupLabelData[groupKey] = {{ maxY: topY, xPos, zPos, folders: [], scenePath }};
            }}
            if (topY > groupLabelData[groupKey].maxY) {{
                groupLabelData[groupKey].maxY = topY;
                groupLabelData[groupKey].xPos = xPos;
                groupLabelData[groupKey].zPos = zPos;
            }}
            groupLabelData[groupKey].folders.push({{ folderName, relPath, imageCount: stackImages.length, xPos, zPos, topY }});
        }}

        // Create spatial labels from recursive tree
        const scenePath = node.path || '';
        let hoverDimTimeout = null;

        function applyDimming(targetPath) {{
            for (const [folder, data] of Object.entries(stackGroups)) {{
                const isMatch = folder.startsWith(targetPath + '/') || folder === targetPath;
                const isAncestor = targetPath.startsWith(folder + '/');
                const op = (isMatch || isAncestor) ? 1.0 : STACK_DIM_OPACITY;
                data.materials.forEach(m => m.opacity = op);
            }}
            stackLabels.forEach(sl => {{
                const isMatch = sl.folderName.startsWith(targetPath + '/') || sl.folderName === targetPath;
                const isAncestor = targetPath.startsWith(sl.folderName + '/');
                sl.element.style.opacity = (isMatch || isAncestor) ? '1.0' : String(STACK_DIM_OPACITY);
            }});
        }}

        function clearDimming() {{
            for (const data of Object.values(stackGroups)) data.materials.forEach(m => m.opacity = 1.0);
            stackLabels.forEach(sl => sl.element.style.opacity = '1.0');
        }}

        function setNavVisible(parentPath) {{
            activeLabelPath = parentPath;
            stackLabels.forEach(sl => {{
                if (sl.isGroup) return;
                const isDirectChild = sl.navParentPath === parentPath;
                const isAncestorChild = parentPath.startsWith(sl.navParentPath + '/');
                sl.navVisible = isDirectChild || isAncestorChild;
            }});
        }}

        function clearNav() {{
            activeLabelPath = null;
            activeGroupPath = null;
            stackLabels.forEach(sl => {{
                if (!sl.isGroup) sl.navVisible = false;
            }});
        }}

        // Build a position tree from flat folder list per group
        function buildPositionTree(folders, basePath) {{
            const root = {{ children: {{}}, path: basePath, maxY: 0, xPos: 0, zPos: 0 }};
            for (const f of folders) {{
                const sub = f.relPath.split('/').filter(p => p).slice(1);
                let cur = root;
                let curPath = basePath;
                for (let i = 0; i < sub.length; i++) {{
                    curPath = curPath + '/' + sub[i];
                    if (!cur.children[sub[i]]) {{
                        cur.children[sub[i]] = {{ children: {{}}, path: curPath, maxY: 0, xPos: f.xPos, zPos: f.zPos }};
                    }}
                    cur = cur.children[sub[i]];
                }}
                if (f.topY > cur.maxY) {{
                    cur.maxY = f.topY;
                    cur.xPos = f.xPos;
                    cur.zPos = f.zPos;
                }}
            }}
            function propagate(n) {{
                for (const child of Object.values(n.children)) {{
                    propagate(child);
                    if (child.maxY > n.maxY) {{
                        n.maxY = child.maxY;
                        n.xPos = child.xPos;
                        n.zPos = child.zPos;
                    }}
                }}
            }}
            propagate(root);
            return root;
        }}

        function createLabel(name, path, worldPos, isGroup, navParentPath, rootGroupPath) {{
            const el = document.createElement('span');
            el.className = 'stack-label' + (isGroup ? '' : ' nav-child-label');
            el.dataset.folderName = path;
            el.innerHTML = `<span style="padding:2px 4px;cursor:pointer" data-path="${{path}}">${{name}}</span>`;
            el.addEventListener('wheel', (e) => {{ e.stopPropagation(); renderer.domElement.dispatchEvent(new WheelEvent('wheel', e)); }}, {{ passive: false }});
            labelContainer.appendChild(el);

            const entry = {{ element: el, position: worldPos, xPos: worldPos.x, zPos: worldPos.z, folderName: path, isGroup, isAncestor: false, navParentPath, navVisible: false }};
            stackLabels.push(entry);

            el.addEventListener('mouseenter', () => {{
                clearTimeout(hoverDimTimeout);
                if (currentFocusedParent || mouseIsDown) return;
                activeGroupPath = rootGroupPath;
                setNavVisible(path);
                applyDimming(path);
            }});
            el.addEventListener('mouseleave', () => {{
                hoverDimTimeout = setTimeout(() => {{
                    if (currentFocusedParent) return;
                    if (activeGroupPath === rootGroupPath) return;
                    clearNav();
                    clearDimming();
                }}, spriteConfig.submenu_close_delay);
            }});

            el.querySelector('span[data-path]').onclick = (e) => {{
                e.stopPropagation();
                const clickedNode = findNodeByPath(dataTree, path);
                if (clickedNode && clickedNode.path === node.path) focusStackGroup(path);
                else if (clickedNode) renderContent(clickedNode);
            }};

            return entry;
        }}

        function createChildLabels(treeNode, parentPath, rootGroupPath) {{
            for (const [name, child] of Object.entries(treeNode.children)) {{
                const wp = new THREE.Vector3(child.xPos, child.maxY, child.zPos);
                createLabel(name, child.path, wp, false, parentPath, rootGroupPath);
                if (Object.keys(child.children).length > 0) {{
                    createChildLabels(child, child.path, rootGroupPath);
                }}
            }}
        }}

        for (const [groupKey, gData] of Object.entries(groupLabelData)) {{
            const groupPath = scenePath ? scenePath + '/' + groupKey : groupKey;
            const worldPos = new THREE.Vector3(gData.xPos, gData.maxY, gData.zPos);
            const entry = createLabel(groupKey, groupPath, worldPos, true, null, groupPath);

            // Ancestor labels above group label
            const ancestorParts = scenePath ? scenePath.split('/') : [];
            for (let ai = 0; ai < ancestorParts.length; ai++) {{
                const aPath = ancestorParts.slice(0, ai + 1).join('/');
                const aName = ancestorParts[ai];
                const aEl = document.createElement('span');
                aEl.className = 'stack-label nav-ancestor-label';
                aEl.dataset.folderName = aPath;
                aEl.innerHTML = `<span style="padding:2px 4px;cursor:pointer;color:#888" data-path="${{aPath}}">${{aName}}</span>`;
                aEl.addEventListener('wheel', (e) => {{ e.stopPropagation(); renderer.domElement.dispatchEvent(new WheelEvent('wheel', e)); }}, {{ passive: false }});
                labelContainer.appendChild(aEl);
                aEl.addEventListener('mouseenter', () => {{
                    clearTimeout(hoverDimTimeout);
                }});
                aEl.addEventListener('mouseleave', () => {{
                    hoverDimTimeout = setTimeout(() => {{
                        if (currentFocusedParent) return;
                        clearNav();
                        clearDimming();
                    }}, spriteConfig.submenu_close_delay);
                }});
                aEl.querySelector('span[data-path]').onclick = (e) => {{
                    e.stopPropagation();
                    const clickedNode = findNodeByPath(dataTree, aPath);
                    if (clickedNode) renderContent(clickedNode);
                }};
                const ancestorOffset = (ancestorParts.length - ai) * 28;
                stackLabels.push({{ element: aEl, position: worldPos, xPos: gData.xPos, zPos: gData.zPos, folderName: aPath, isGroup: false, isAncestor: true, ancestorOffset, anchorGroup: groupPath, navParentPath: null, navVisible: false }});
            }}

            const posTree = buildPositionTree(gData.folders, groupPath);
            createChildLabels(posTree, groupPath, groupPath);
        }}
    }})();

    const bgLodPromise = loadingPromise.then(async () => {{
        const allSSArrays = new Set();
        folders.forEach(folder => {{
            grouped[folder].forEach(img => allSSArrays.add(JSON.stringify(img.ss)));
        }});
        const uniqueSSArrays = [...allSSArrays].map(s => JSON.parse(s));
        const waitFrame = () => new Promise(r => requestAnimationFrame(r));
        for (let lod = LOD_COUNT - 2; lod >= 0; lod--) {{
            const paths = uniqueSSArrays.map(ss => ss[lod]);
            for (const p of paths) {{
                await loadSpritesheet(p);
                await waitFrame();
            }}
        }}
    }});

    const sceneMaterials = new Set();
    loadingPromise.then(() => {{
        for (const data of Object.values(stackGroups))
            for (const mat of data.materials) sceneMaterials.add(mat);
    }});

    // const stats = new Stats();
    // stats.showPanel(0);
    // container.appendChild(stats.dom);
    // stats.dom.style.position = 'absolute';
    // stats.dom.style.top = '30px';
    // stats.dom.style.left = '5px';

    const resizeHandler = () => {{
        const newAspect = container.clientWidth / container.clientHeight;
        camera.left = frustumSize * newAspect / -2;
        camera.right = frustumSize * newAspect / 2;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    }};

    // const sceneData = {{ scene, renderer, camera, controls, animationId: null, resizeHandler, stats, labelContainer, countDiv, stackGroups, focusStackGroup, unfocusAll }};
    const sceneData = {{ scene, renderer, camera, controls, animationId: null, resizeHandler, labelContainer, countDiv, stackGroups, focusStackGroup, unfocusAll }};

    const frustum = new THREE.Frustum();
    const cameraViewProjectionMatrix = new THREE.Matrix4();

    let frameCount = 0;
    
    // OPTIMIZATION SETTINGS


    const MAX_LABELS =  spriteConfig.max_labels;
    const SCREEN_BUFFER = spriteConfig.screen_buffer;
    const _labelVec = new THREE.Vector3();
    const _worldBox = new THREE.Box3();

    function animate() {{
        sceneData.animationId = requestAnimationFrame(animate);
        controls.update();
        const rotationAngle = Date.now() * ROTATION_SPEED;
        scene.rotation.y = rotationAngle;
        
        if (frameCount % 5 === 0) {{
            camera.updateMatrixWorld();
            cameraViewProjectionMatrix.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
            frustum.setFromProjectionMatrix(cameraViewProjectionMatrix);
            for (const [folder, data] of Object.entries(stackGroups)) {{
                if (!data.localBox) {{
                    data.localBox = new THREE.Box3().setFromObject(data.group);
                    data.group.updateMatrixWorld();
                    data.localBox.applyMatrix4(data.group.matrixWorld.clone().invert());
                }}
                _worldBox.copy(data.localBox).applyMatrix4(data.group.matrixWorld);
                data.group.visible = frustum.intersectsBox(_worldBox);
            }}
        }}

        if (frameCount % 15 === 0) {{
            const viewHeight = (camera.top - camera.bottom) / camera.zoom;
            const targetLod = viewHeight < 10 ? 0 : viewHeight < 40 ? 1 : 2;
            for (const mat of sceneMaterials) {{
                if (!mat._ssArray) continue;
                const best = getBestLod(mat._ssArray, targetLod);
                if (best && mat.map !== best) {{ mat.map = best; mat.needsUpdate = true; }}
            }}
        }}
        
        // OPTIMIZED LABEL UPDATE (Every frame, but efficient)
        if (labelsVisible) {{
            const cWidth = container.clientWidth;
            const cHeight = container.clientHeight;
            const cCenterX = cWidth / 2;
            const cCenterY = cHeight / 2;

            const labelCandidates = [];

            const cosR = Math.cos(rotationAngle);
            const sinR = Math.sin(rotationAngle);

            // 1. Calculate positions and filter roughly
            for (let i = 0; i < stackLabels.length; i++) {{
                const lbl = stackLabels[i];

                if (lbl.isAncestor) {{
                    if (activeGroupPath !== lbl.anchorGroup) {{
                        if (lbl.element.style.display !== 'none') lbl.element.style.display = 'none';
                        continue;
                    }}
                }} else if (!lbl.isGroup && !lbl.navVisible) {{
                    if (lbl.element.style.display !== 'none') lbl.element.style.display = 'none';
                    continue;
                }}
                
                // Manual World Rotation
                const rX = lbl.xPos * cosR + lbl.zPos * sinR;
                const rZ = -lbl.xPos * sinR + lbl.zPos * cosR;
                
                // Quick Depth Check (is it behind camera?)
                // Simple heuristic since we know camera is roughly at +Z
                // But camera rotates. So we use projection.
                
                const vec = _labelVec.set(rX, lbl.position.y, rZ);
                vec.project(camera);
                
                // vec.x and vec.y are now -1 to 1
                // Check bounds with buffer
                if (vec.z < 1 && vec.x >= -1.2 && vec.x <= 1.2 && vec.y >= -1.2 && vec.y <= 1.2) {{
                    const screenX = (vec.x * 0.5 + 0.5) * cWidth;
                    const screenY = (-(vec.y * 0.5) + 0.5) * cHeight;
                    
                    // Calculate distance to center of screen for priority
                    const dist = Math.abs(screenX - cCenterX) + Math.abs(screenY - cCenterY);
                    
                    labelCandidates.push({{
                        el: lbl.element,
                        x: screenX,
                        y: lbl.isAncestor ? screenY - lbl.ancestorOffset : screenY,
                        anchorY: screenY,
                        d: dist
                    }});
                }} else {{
                    if (lbl.element.style.display !== 'none') lbl.element.style.display = 'none';
                }}
            }}

            // 1b. Resolve overlapping labels with predictable vertical offset
            const OVERLAP_THRESH = 30;
            const LABEL_OFFSET_Y = 28;
            labelCandidates.sort((a, b) => a.el.dataset.folderName < b.el.dataset.folderName ? -1 : 1);
            for (let i = 0; i < labelCandidates.length; i++) {{
                for (let j = i + 1; j < labelCandidates.length; j++) {{
                    const dx = Math.abs(labelCandidates[i].x - labelCandidates[j].x);
                    const dy = Math.abs(labelCandidates[i].y - labelCandidates[j].y);
                    if (dx < OVERLAP_THRESH && dy < OVERLAP_THRESH) {{
                        labelCandidates[j].y = labelCandidates[i].y + LABEL_OFFSET_Y;
                    }}
                }}
            }}

            // 2. Sort by distance to center screen
            labelCandidates.sort((a, b) => a.d - b.d);

            // 3. Render top N, hide rest
            for (let i = 0; i < labelCandidates.length; i++) {{
                const cand = labelCandidates[i];
                if (i < MAX_LABELS) {{
                    if (cand.el.style.display !== 'block') cand.el.style.display = 'block';
                    cand.el.style.transform = `translate3d(${{cand.x.toFixed(1)}}px, ${{cand.y.toFixed(1)}}px, 0)`;
                    cand.el._screenX = cand.x;
                    cand.el._screenY = cand.y;
                    cand.el._screenVisible = true;
                }} else {{
                    if (cand.el.style.display !== 'none') cand.el.style.display = 'none';
                    cand.el._screenVisible = false;
                }}
            }}

            // 4. Wire system
            const WIRE = {{ r: 12, pad: 20, biasMin: 80, biasRange: 120, arrowSize: 6, arrowMinLen: 400 }};

            function roundCorner(d, a, c, b, maxR) {{
                const d1x = c.x-a.x, d1y = c.y-a.y, d2x = b.x-c.x, d2y = b.y-c.y;
                const l1 = Math.hypot(d1x, d1y), l2 = Math.hypot(d2x, d2y);
                const r = Math.min(maxR, l1*0.45, l2*0.45);
                if (r < 1) return d + ` L ${{c.x}} ${{c.y}}`;
                return d + ` L ${{c.x-d1x/l1*r}} ${{c.y-d1y/l1*r}} Q ${{c.x}} ${{c.y}}, ${{c.x+d2x/l2*r}} ${{c.y+d2y/l2*r}}`;
            }}

            function routeWire(a, b) {{
                const {{ r: R, pad: P, biasMin: bm, biasRange: br }} = WIRE;
                let wp;
                if (b.x > a.x + P) {{
                    const mx = (a.x + b.x) / 2;
                    wp = [{{ x: mx, y: a.y }}, {{ x: mx, y: b.y }}];
                }} else {{
                    const bias = 0.5 + Math.min(Math.max((Math.abs(b.y - a.y) - bm) / br, 0), 1) * 0.35;
                    const rx = Math.max(a.x, b.x) + P, lx = Math.min(a.x, b.x) - P;
                    wp = [{{ x: rx, y: a.y }}, {{ x: rx, y: a.y+(b.y-a.y)*bias }}, {{ x: lx, y: a.y+(b.y-a.y)*bias }}, {{ x: lx, y: b.y }}];
                }}
                const pts = [a, ...wp, b];
                let d = '';
                for (let i = 1; i < pts.length - 1; i++) d = roundCorner(d, pts[i-1], pts[i], pts[i+1], R);
                return {{ d: d + ` L ${{b.x}} ${{b.y}}`, pts }};
            }}

            function wireD(a, b) {{ const w = routeWire(a, b); return {{ d: `M ${{a.x}} ${{a.y}}` + w.d, pts: w.pts }}; }}
            function labelR(el) {{ return {{ x: (el._screenX||0) + (el.offsetWidth||60), y: (el._screenY||0) + (el.offsetHeight||18)/2 }}; }}
            function labelL(el) {{ return {{ x: el._screenX||0, y: (el._screenY||0) + (el.offsetHeight||18)/2 }}; }}

            function chainWires(els) {{
                let d = '';
                const arrows = [];
                for (let i = 0; i < els.length - 1; i++) {{
                    const w = wireD(labelR(els[i]), labelL(els[i+1]));
                    d += w.d;
                    arrows.push(w.pts);
                }}
                return {{ d, arrows }};
            }}

            // Arrow: midpoint of path, chevron pointing in travel direction
            let _arrows = [];
            function queueArrow(pts, dim) {{
                let total = 0;
                const lens = [];
                for (let i = 0; i < pts.length - 1; i++) {{ const l = Math.hypot(pts[i+1].x-pts[i].x, pts[i+1].y-pts[i].y); lens.push(l); total += l; }}
                if (total < WIRE.arrowMinLen) return;
                let target = total / 2, acc = 0;
                for (let i = 0; i < lens.length; i++) {{
                    if (acc + lens[i] >= target) {{
                        const t = (target - acc) / lens[i];
                        _arrows.push({{
                            x: pts[i].x + (pts[i+1].x-pts[i].x)*t,
                            y: pts[i].y + (pts[i+1].y-pts[i].y)*t,
                            a: Math.atan2(pts[i+1].y-pts[i].y, pts[i+1].x-pts[i].x) * 180 / Math.PI,
                            dim
                        }});
                        return;
                    }}
                    acc += lens[i];
                }}
            }}
            function flushArrows() {{
                wireArrowG.innerHTML = '';
                const s = WIRE.arrowSize, ns = 'http://www.w3.org/2000/svg';
                for (const ar of _arrows) {{
                    const g = document.createElementNS(ns, 'g');
                    g.setAttribute('transform', `translate(${{ar.x}},${{ar.y}}) rotate(${{ar.a}})`);
                    g.classList.add('wire-arrow');
                    if (ar.dim) g.classList.add('wire-arrow-dim');
                    for (const dy of [-s, s]) {{
                        const l = document.createElementNS(ns, 'line');
                        l.setAttribute('x1', -s); l.setAttribute('y1', dy); l.setAttribute('x2', 0); l.setAttribute('y2', 0);
                        g.appendChild(l);
                    }}
                    wireArrowG.appendChild(g);
                }}
            }}

            if (activeGroupPath) {{
                _arrows = [];
                const ancestorEls = stackLabels.filter(sl => sl.isAncestor && sl.anchorGroup === activeGroupPath && sl.element.style.display === 'block')
                    .sort((a, b) => b.ancestorOffset - a.ancestorOffset).map(sl => sl.element);
                const gSl = stackLabels.find(sl => sl.isGroup && sl.folderName === activeGroupPath);
                const gEl = gSl && gSl.element.style.display === 'block' ? gSl.element : null;
                const childEls = [];
                if (activeLabelPath && activeLabelPath !== activeGroupPath) {{
                    let cur = activeGroupPath;
                    for (const p of activeLabelPath.slice(activeGroupPath.length + 1).split('/')) {{
                        cur += '/' + p;
                        const cl = stackLabels.find(sl => !sl.isGroup && !sl.isAncestor && sl.folderName === cur && sl.element.style.display === 'block');
                        if (cl) childEls.push(cl.element);
                    }}
                }}

                const anc = gEl ? [...ancestorEls, gEl] : ancestorEls;
                const main = gEl ? [gEl, ...childEls] : childEls;

                const ancW = chainWires(anc);
                wirePathAncestor.setAttribute('d', ancW.d);
                ancW.arrows.forEach(pts => queueArrow(pts, false));

                const mainW = chainWires(main);
                let mainD = mainW.d;
                mainW.arrows.forEach(pts => queueArrow(pts, false));
                const isLeaf = activeLabelPath && !stackLabels.some(sl => !sl.isGroup && !sl.isAncestor && sl.navParentPath === activeLabelPath);
                if (!isLeaf && main.length) {{
                    const mw = wireD(labelR(main[main.length - 1]), {{ x: mouseX, y: mouseY }});
                    mainD += mw.d;
                    queueArrow(mw.pts, false);
                }}
                wirePath.setAttribute('d', mainD);

                const onPath = new Set([...(gEl ? [gEl.dataset.folderName] : []), ...childEls.map(el => el.dataset.folderName)]);
                let dimD = '';
                for (const cel of main) {{
                    const cp = cel.dataset.folderName;
                    for (const sl of stackLabels) {{
                        if (sl.isGroup || sl.isAncestor || !sl.navVisible || sl.navParentPath !== cp || sl.element.style.display !== 'block' || onPath.has(sl.folderName)) continue;
                        const w = wireD(labelR(cel), labelL(sl.element));
                        dimD += w.d;
                        queueArrow(w.pts, true);
                    }}
                }}
                wirePathDim.setAttribute('d', dimD);
                flushArrows();
                wireSvg.style.display = '';
            }} else {{
                wirePath.setAttribute('d', '');
                wirePathAncestor.setAttribute('d', '');
                wirePathDim.setAttribute('d', '');
                wireArrowG.innerHTML = '';
                wireSvg.style.display = 'none';
            }}
        }}

        frameCount++;
        renderer.render(scene, camera);
        // stats.end();
    }}
    animate();

    activeScenes.push(sceneData);
    window.addEventListener('resize', resizeHandler);

    await loadingPromise;
    return sceneData;
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
let isInitialLoad = true;

function updateURL(node) {{
    const path = node.path || '';
    history.pushState(null, '', '?path=' + encodeURIComponent(path)); 
}}

async function renderContent(node) {{
    if (!isInitialLoad) updateURL(node);
    const RANDOM_TEXTDIV_POSITION = spriteConfig.random_textdiv_position;
    const SEED = spriteConfig.seed;

    updateURL(node);
    currentNode = node;
    updateTreeState(true);
    
    for (const key in stackMaterialCache) {{
        if (stackMaterialCache[key]) stackMaterialCache[key].dispose();
        delete stackMaterialCache[key];
    }}
    
    activeScenes.forEach(disposeScene);
    activeScenes = [];
    const contentDiv = document.getElementById('content');
    contentDiv.innerHTML = '';
   
    const scenePromises = []; 
    let children = node.children.length > 0 ? node.children : [node];
    children = children.filter(child => (child.ai.length > 0 || child.at.length > 0) && !child.hid);
    
    const count = children.length;
    const cols = Math.ceil(Math.sqrt(count));
    
    for (const child of children) {{
        const div = document.createElement('div');
        div.className = 'content-div';
        div.style.width = `calc(${{100/cols}}% - 2px)`;
        div.style.height = count <= 2 ? '100%' : `calc(${{100/Math.ceil(count/cols)}}% - 2px)`;

        const label = document.createElement('div');
        label.className = 'div-label';
        label.innerHTML = breadcrumbHtml(child.path, currentNode ? currentNode.path : null);
            
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
            
            // 1. Create a Wrapper for Text + Nav (This stays fixed)
            const textWrapper = document.createElement('div');
            textWrapper.style.flex = '3';
            textWrapper.style.position = 'relative'; // Anchor for the Nav
            textWrapper.style.borderLeft = '1px solid #333';
            textWrapper.style.boxSizing = 'border-box';
            //textWrapper.style.border = '1px solid white';
            textWrapper.style.overflow = 'hidden';   // The wrapper does NOT scroll

            // 2. Create the Scrollable Text Area
            const textDiv = document.createElement('div');
            textDiv.className = 'text-content';
            textDiv.style.width = '100%';
            textDiv.style.height = '100%';
            textDiv.style.overflowY = 'auto'; // The text scrolls INSIDE here
            textDiv.style.position = 'absolute'; // Fill the wrapper
            textDiv.style.top = '0';
            textDiv.style.left = '0';

            let htmlParts = [];
            for (const path of child.at) {{
                htmlParts.push(await loadText(path));
            }}
            
textDiv.innerHTML = assembleHtmlParts(htmlParts, child.at);

const scriptTags = textDiv.querySelectorAll('script');
scriptTags.forEach(oldScript => {{
    const newScript = document.createElement('script');
    newScript.textContent = oldScript.textContent;
    oldScript.parentNode.replaceChild(newScript, oldScript);
}});

            // 4. Assemble
            textWrapper.appendChild(textDiv);

            // 5. Image Side
            const imgDiv = document.createElement('div');
            imgDiv.style.flex = '3';
            imgDiv.style.position = 'relative';
            imgDiv.style.borderLeft = '1px solid #333';
            imgDiv.style.boxSizing = 'border-box';
            imgDiv.style.overflow = 'hidden';

            if (RANDOM_TEXTDIV_POSITION) {{
                const seed = child.path.split('').reduce((a, c) => a + c.charCodeAt(0), 0) * SEED;
                const rand = seededRandom(seed);
                if (rand < 0.5) {{ div.appendChild(textWrapper); div.appendChild(imgDiv); }}
                else {{ div.appendChild(imgDiv); div.appendChild(textWrapper); }}
            }} else {{
                 div.appendChild(textWrapper); div.appendChild(imgDiv);
            }}
            
            div._sceneContainer = imgDiv;
            div._sceneChild = child;


        }} else if (child.ai.length > 0) {{
            div._sceneContainer = div;
            div._sceneChild = child;
       }} else if (child.at.length > 0) {{
            div.className = 'content-div';
            div.style.position = 'relative';
            div.style.overflow = 'hidden';
            
            const textDiv = document.createElement('div');
            textDiv.className = 'text-content';
            textDiv.style.width = '100%';
            textDiv.style.height = '100%';
            textDiv.style.overflowY = 'auto';
            textDiv.style.position = 'absolute';
            textDiv.style.top = '0';
            textDiv.style.left = '0';
            
            let htmlParts = [];
            for (const path of child.at) {{ htmlParts.push(await loadText(path)); }}
            textDiv.innerHTML = assembleHtmlParts(htmlParts, child.at);
            
            const scriptTags = textDiv.querySelectorAll('script');
            scriptTags.forEach(oldScript => {{
                const newScript = document.createElement('script');
                newScript.textContent = oldScript.textContent;
                oldScript.parentNode.replaceChild(newScript, oldScript);
            }});
            
            const labelHtml = breadcrumbHtml(child.path, currentNode ? currentNode.path : null);
            
            const labelDiv = document.createElement('div');
            labelDiv.className = 'div-label';
            labelDiv.innerHTML = labelHtml;
            labelDiv.querySelectorAll('span[data-path]').forEach(span => {{
                span.onclick = (e) => {{
                    e.stopPropagation();
                    const node = findNodeByPath(dataTree, span.dataset.path);
                    if (node) renderContent(node);
                }};
            }});
            
            
            div.appendChild(textDiv);
            div.appendChild(labelDiv);
        }}
        const EDGE_ZONE = 35;
        const TOP_DEADZONE = 40;
        const BOTTOM_DEADZONE = 40;

        const parentPath = currentNode ? currentNode.path.split('/').slice(0, -1).join('/') : null;
        const hasParent = parentPath !== null && parentPath !== '';
        const canGoDeeper = child !== node;
        const isRoot = !hasParent;
        const isLeaf = !canGoDeeper;

        const leftBox = document.createElement('div');
        leftBox.className = 'edge-nav-box edge-nav-left' + (isRoot ? ' edge-nav-end' : '');
        div.appendChild(leftBox);
        if (hasParent) {{
            leftBox.addEventListener('click', (e) => {{
                e.stopPropagation();
                const parentNode = findNodeByPath(dataTree, parentPath);
                if (parentNode) renderContent(parentNode);
            }});
        }}

        const rightBox = document.createElement('div');
        rightBox.className = 'edge-nav-box edge-nav-right' + (isLeaf ? ' edge-nav-end' : '');
        div.appendChild(rightBox);
        if (canGoDeeper) {{
            rightBox.addEventListener('click', (e) => {{
                e.stopPropagation();
                renderContent(child);
            }});
        }}

        div.addEventListener('mousemove', (e) => {{
            const rect = div.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const h = rect.height;
            const inDeadzone = y < TOP_DEADZONE || y > h - BOTTOM_DEADZONE;
            if (!inDeadzone && x < EDGE_ZONE) {{
                leftBox.style.display = 'block';
                leftBox.style.top = (y - 15) + 'px';
            }} else leftBox.style.display = 'none';
            if (!inDeadzone && x > rect.width - EDGE_ZONE) {{
                rightBox.style.display = 'block';
                rightBox.style.top = (y - 15) + 'px';
            }} else rightBox.style.display = 'none';
        }});
        div.addEventListener('mouseleave', () => {{
            leftBox.style.display = 'none';
            rightBox.style.display = 'none';
        }});

        contentDiv.appendChild(div);
    }}

    requestAnimationFrame(() => {{
        const el = document.elementFromPoint(window._lastEdgeNavX || 0, window._lastEdgeNavY || 0);
        if (el) el.dispatchEvent(new MouseEvent('mousemove', {{
            clientX: window._lastEdgeNavX || 0,
            clientY: window._lastEdgeNavY || 0,
            bubbles: true
        }}));
    }});

    await new Promise(resolve => requestAnimationFrame(resolve));
    const sceneDivs = Array.from(contentDiv.children).filter(d => d._sceneContainer);
    for (const div of sceneDivs) {{
        scenePromises.push(createThreeScene(div._sceneContainer, div._sceneChild.ai, div._sceneChild));
    }}
    await Promise.all(scenePromises);
    return Promise.resolve();
}}
</script>
</body>
</html>''')









print("Generated spritesheets, data.json and index.html")