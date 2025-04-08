from flask import Flask, render_template, request, send_file, jsonify
import os
import io
import base64
import json
import random
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Set the backend to Agg for headless environments
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
import randomname  # Add import for randomname package

app = Flask(__name__)
app.config['SECRET_KEY'] = 'synthetic-data-generator'

# Ensure directories exist
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'generated')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Lists for random name generation
RANDOM_CATEGORY_NAMES = [
    "Products", "Regions", "Departments", "Industries", "Sectors",
    "Markets", "Segments", "Divisions", "Platforms", "Channels",
    "Teams", "Projects", "Services", "Solutions", "Technologies",
    "Countries", "Cities", "Groups", "Clusters", "Verticals"
]

RANDOM_SUBCATEGORY_NAMES = [
    "Sales", "Revenue", "Growth", "Costs", "Profits",
    "Customers", "Users", "Metrics", "Conversion", "Retention",
    "Engagement", "Adoption", "Performance", "Efficiency", "Quality",
    "Satisfaction", "Impact", "Value", "ROI", "Margin"
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_file('static/stack-app.svg', mimetype='image/svg+xml')

@app.route('/generate', methods=['POST'])
def generate():
    # Get parameters from the form
    params = {
        'num_categories': int(request.form.get('num_categories', 5)),
        'num_subcategories': int(request.form.get('num_subcategories', 3)),
        'min_value': float(request.form.get('min_value', 0)),
        'max_value': float(request.form.get('max_value', 100)),
        'theme': request.form.get('theme', 'default'),
        'title': request.form.get('title', 'Stack Bar Chart'),
        'xlabel': request.form.get('xlabel', 'Categories'),
        'ylabel': request.form.get('ylabel', 'Values'),
        'include_grid': request.form.get('include_grid', 'true') == 'true',
        'error_type': request.form.get('error_type', 'none'),
        'error_probability': float(request.form.get('error_probability', 0.1)),
        'width': int(request.form.get('width', 800)),
        'height': int(request.form.get('height', 600)),
        'dpi': int(request.form.get('dpi', 100)),
        # New parameters for category and subcategory naming
        'naming_type': request.form.get('naming_type', 'default'),  # 'default', 'custom', 'random'
        'custom_categories': request.form.get('custom_categories', ''),
        'custom_subcategories': request.form.get('custom_subcategories', '')
    }
    
    # Generate data and image
    data = generate_data(params)
    img_data, data_json = generate_chart(data, params)
    
    return jsonify({
        'image': img_data,
        'data': data_json
    })

@app.route('/batch_generate', methods=['POST'])
def batch_generate():
    # Get parameters from the form
    params_str = request.form.get('params', '{}')
    params = json.loads(params_str)
    count = int(request.form.get('count', 10))
    
    # Ensure numeric parameters are properly typed
    for key in ['num_categories', 'num_subcategories', 'min_value', 'max_value', 'width', 'height', 'dpi']:
        if key in params:
            params[key] = float(params[key]) if key in ['min_value', 'max_value'] else int(params[key])
    
    # Ensure error_probability is a float
    if 'error_probability' in params:
        params['error_probability'] = float(params['error_probability'])
    else:
        params['error_probability'] = 0.1  # Default value
    
    # Get batch specific parameters
    min_categories = int(request.form.get('min_categories', 3))
    max_categories = int(request.form.get('max_categories', 8))
    min_subcategories = int(request.form.get('min_subcategories', 2))
    max_subcategories = int(request.form.get('max_subcategories', 5))
    
    results = []
    for i in range(count):
        # Randomize some parameters for variety
        current_params = params.copy()
        current_params['num_categories'] = random.randint(min_categories, max_categories)
        current_params['num_subcategories'] = random.randint(min_subcategories, max_subcategories)
        
        # Ensure these are numeric types
        if 'min_value' in current_params:
            current_params['min_value'] = float(current_params['min_value'])
        if 'max_value' in current_params:
            current_params['max_value'] = float(current_params['max_value'])
        
        # Generate data and image
        data = generate_data(current_params)
        img_data, data_json = generate_chart(data, current_params)
        
        results.append({
            'image': img_data,
            'data': data_json,
            'params': current_params
        })
    
    return jsonify(results)

@app.route('/download', methods=['POST'])
def download():
    try:
        # Improved request data handling
        try:
            data = request.get_json(force=True, silent=True)  # More robust JSON parsing
            if not data:
                # Try form data as fallback
                data = request.form.to_dict()
                if 'images' in data and isinstance(data['images'], str):
                    data['images'] = json.loads(data['images'])
        except Exception as json_error:
            print(f"JSON parsing error: {json_error}")
            return jsonify({'status': 'error', 'message': f'Invalid JSON data: {str(json_error)}'})
        
        if not data or 'images' not in data or not data['images']:
            return jsonify({'status': 'error', 'message': 'No images data provided'})
        
        # Create a timestamped folder for this batch
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        batch_folder = os.path.join(UPLOAD_FOLDER, f'batch_{timestamp}')
        os.makedirs(batch_folder, exist_ok=True)
        
        # Path for the master JSON file that will contain all generations
        master_json_path = os.path.join(UPLOAD_FOLDER, 'all_generated_images.json')
        batch_json_path = os.path.join(batch_folder, 'batch_data.json')
        
        # Prepare data structure for saving
        batch_data = {
            'batch_id': f'batch_{timestamp}',
            'generation_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'image_count': 0,
            'images': []
        }
        
        # Process each image with more robust error handling
        successful_images = 0
        failed_images = 0
        
        for i, item in enumerate(data['images']):
            try:
                # Validate item structure
                if not isinstance(item, dict):
                    print(f"Invalid image data format for image {i}: {type(item)}")
                    failed_images += 1
                    continue
                
                # Extract image data with better error handling
                if 'image' not in item or not item['image']:
                    print(f"Missing image data for image {i}")
                    failed_images += 1
                    continue
                
                img_data_parts = item['image'].split('base64,')
                if len(img_data_parts) != 2:
                    print(f"Invalid image data format for image {i}")
                    failed_images += 1
                    continue
                    
                img_data = img_data_parts[1]
                params = item.get('params', {})
                chart_data = item.get('data', {})
                
                # Generate a filename
                filename = f'image_{i+1}.png'
                filepath = os.path.join(batch_folder, filename)
                
                # Save image to file with error handling
                try:
                    with open(filepath, 'wb') as f:
                        f.write(base64.b64decode(img_data))
                    successful_images += 1
                except Exception as file_error:
                    print(f"Error writing image file {i}: {file_error}")
                    failed_images += 1
                    continue
                
                # Get relative URL
                relative_url = os.path.join('static', 'generated', f'batch_{timestamp}', filename)
                
                # Create a structured record for this image
                image_record = {
                    'file_name': filename,
                    'file_url': relative_url,
                    'generation_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'chart_title': params.get('title', 'Untitled Chart'),
                    'chart_type': 'Stacked Bar Chart',
                    'parameters': params,
                    'data_summary': {}
                }
                
                # Process and restructure chart data
                if chart_data:
                    try:
                        # Convert to pandas DataFrame for summary statistics
                        chart_df = pd.DataFrame(chart_data)
                        
                        # Add summary statistics
                        image_record['data_summary'] = {
                            'sum': float(chart_df.values.sum()),
                            'mean': float(chart_df.values.mean()),
                            'min': float(chart_df.values.min()),
                            'max': float(chart_df.values.max())
                        }
                        
                        # Restructure data as arrays by category
                        categories_data = []
                        for category_idx, category in enumerate(chart_df.index):
                            category_data = {
                                'name': category,
                                'subcategories': []
                            }
                            
                            # Add subcategory values
                            for subcategory in chart_df.columns:
                                category_data['subcategories'].append({
                                    'name': subcategory,
                                    'value': float(chart_df[subcategory][category])
                                })
                            
                            categories_data.append(category_data)
                        
                        image_record['categories'] = categories_data
                        
                    except Exception as data_error:
                        print(f"Error processing chart data for image {i}: {data_error}")
                        image_record['data_error'] = str(data_error)
                
                # Add to batch data
                batch_data['images'].append(image_record)
                
            except Exception as e:
                print(f"Error processing image {i}: {e}")
                failed_images += 1
                continue  # Skip this image but continue processing others
        
        # Update image count
        batch_data['image_count'] = successful_images
        batch_data['failed_count'] = failed_images
        
        # Save batch data to JSON file
        try:
            with open(batch_json_path, 'w') as f:
                json.dump(batch_data, f, indent=2)
            
            # Handle master JSON file
            master_data = {'batches': []}
            if os.path.exists(master_json_path):
                try:
                    with open(master_json_path, 'r') as f:
                        master_data = json.load(f)
                except Exception as json_error:
                    print(f"Error reading master JSON file: {json_error}")
                    # If reading fails, create a backup and start fresh
                    if os.path.exists(master_json_path):
                        backup_path = os.path.join(UPLOAD_FOLDER, f'all_generated_images_backup_{timestamp}.json')
                        os.rename(master_json_path, backup_path)
            
            # Add batch summary to master data
            batch_summary = {
                'batch_id': batch_data['batch_id'],
                'generation_time': batch_data['generation_time'],
                'image_count': batch_data['image_count'],
                'path': os.path.join('static', 'generated', f'batch_{timestamp}', 'batch_data.json')
            }
            
            # Ensure batches exists and is a list
            if 'batches' not in master_data or not isinstance(master_data['batches'], list):
                master_data['batches'] = []
            
            master_data['batches'].append(batch_summary)
            
            # Save updated master data
            with open(master_json_path, 'w') as f:
                json.dump(master_data, f, indent=2)
            
            # Return success with paths to the JSON files
            return jsonify({
                'status': 'success', 
                'batch_json_url': os.path.join('static', 'generated', f'batch_{timestamp}', 'batch_data.json'),
                'master_json_url': os.path.join('static', 'generated', 'all_generated_images.json'),
                'image_count': successful_images,
                'failed_count': failed_images,
                'batch_folder': f'batch_{timestamp}'
            })
        except Exception as save_error:
            print(f"Error saving JSON files: {save_error}")
            return jsonify({
                'status': 'partial_success',
                'message': f'Images saved but JSON generation failed: {str(save_error)}',
                'image_count': successful_images,
                'failed_count': failed_images,
                'batch_folder': f'batch_{timestamp}'
            })
        
        return jsonify({'status': 'error', 'message': 'No images were successfully processed'})
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Download error: {e}\n{error_details}")
        return jsonify({
            'status': 'error', 
            'message': f'Error during download: {str(e)}',
            'details': error_details
        })

def generate_data(params):
    num_categories = params['num_categories']
    num_subcategories = params['num_subcategories']
    min_value = float(params['min_value'])  # Ensure it's float
    max_value = float(params['max_value'])  # Ensure it's float
    naming_type = params.get('naming_type', 'default')
    
    # Create category and subcategory names based on naming type
    if naming_type == 'custom':
        # Parse custom names from comma-separated strings
        custom_categories = params.get('custom_categories', '')
        custom_subcategories = params.get('custom_subcategories', '')
        
        categories = [name.strip() for name in custom_categories.split(',') if name.strip()]
        subcategories = [name.strip() for name in custom_subcategories.split(',') if name.strip()]
        
        # If not enough custom names provided, fill the rest with default names
        if len(categories) < num_categories:
            categories.extend([f'Category {i+1}' for i in range(len(categories), num_categories)])
        else:
            categories = categories[:num_categories]  # Trim if too many provided
            
        if len(subcategories) < num_subcategories:
            subcategories.extend([f'Subcategory {i+1}' for i in range(len(subcategories), num_subcategories)])
        else:
            subcategories = subcategories[:num_subcategories]  # Trim if too many provided
    
    elif naming_type == 'random':
        # Generate random meaningful names from predefined lists
        categories = generate_random_names(RANDOM_CATEGORY_NAMES, num_categories)
        subcategories = generate_random_names(RANDOM_SUBCATEGORY_NAMES, num_subcategories)
    
    elif naming_type == 'randomname':
        # Use the randomname library for more variety
        categories = [randomname.get_name() for _ in range(num_categories)]
        subcategories = [randomname.get_name() for _ in range(num_subcategories)]
    
    else:  # default naming
        categories = [f'Category {i+1}' for i in range(num_categories)]
        subcategories = [f'Subcategory {i+1}' for i in range(num_subcategories)]
    
    # Generate random data
    data = {}
    for subcategory in subcategories:
        data[subcategory] = np.random.uniform(min_value/num_subcategories, 
                                             max_value/num_subcategories, 
                                             num_categories)
    
    # Convert to DataFrame
    df = pd.DataFrame(data, index=categories)
    return df

def generate_random_names(name_list, count):
    """Generate a list of random names without repeating if possible."""
    if len(name_list) >= count:
        # If we have enough names, randomly sample without replacement
        return random.sample(name_list, count)
    else:
        # If we don't have enough names, use all names plus numbered extras
        result = name_list.copy()
        for i in range(count - len(name_list)):
            # Generate a random name with a number suffix
            base_name = random.choice(name_list)
            result.append(f"{base_name} {i+1}")
        return result

def generate_chart(data, params):
    # Extract parameters
    theme = params['theme']
    title = params['title']
    xlabel = params['xlabel']
    ylabel = params['ylabel']
    include_grid = params['include_grid']
    error_type = params['error_type']
    # Ensure error_probability is a float
    error_probability = float(params.get('error_probability', 0.1))
    width = params['width'] / 100
    height = params['height'] / 100
    dpi = params['dpi']
    
    # Create figure before applying styles
    plt.style.use('default')  # Reset to default style first
    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
    
    # Apply enhanced theme styles
    if theme == 'dark':
        plt.style.use('dark_background')
        ax.set_facecolor('#121212')
        fig.patch.set_facecolor('#121212')
        title_color = '#ffffff'
        label_color = '#dddddd'
        grid_color = '#333333'
        colors = plt.cm.plasma(np.linspace(0, 0.9, len(data.columns)))
    elif theme == 'seaborn':
        plt.style.use('seaborn-v0_8')
        ax.set_facecolor('#f0f0f8')
        fig.patch.set_facecolor('#f0f0f8')
        title_color = '#102050'
        label_color = '#2a3f5f'
        grid_color = '#cccccc'
        # Create a custom color palette similar to seaborn's colorblind
        colors = plt.cm.Set2(np.linspace(0, 1, len(data.columns)))
    elif theme == 'bmh':
        plt.style.use('bmh')
        ax.set_facecolor('#f5f5f2')
        fig.patch.set_facecolor('#f5f5f2')
        title_color = '#513D2B'
        label_color = '#513D2B'
        grid_color = '#cccccc'
        # Earth tone color palette
        cmap = LinearSegmentedColormap.from_list('bmh_custom', ['#8B4513', '#A0522D', '#CD853F', '#DEB887', '#F5DEB3'])
        colors = cmap(np.linspace(0, 1, len(data.columns)))
    elif theme == 'ggplot':
        plt.style.use('ggplot')
        ax.set_facecolor('#f0f0f0')
        fig.patch.set_facecolor('#f0f0f0')
        title_color = '#555555'
        label_color = '#555555'
        grid_color = '#dddddd'
        # Vibrant color palette inspired by ggplot2
        colors = plt.cm.tab10(np.linspace(0, 0.8, len(data.columns)))
    else:  # default
        ax.set_facecolor('#ffffff')
        fig.patch.set_facecolor('#ffffff')
        title_color = '#000000'
        label_color = '#000000'
        grid_color = '#cccccc'
        colors = plt.cm.tab10(np.linspace(0, 1, len(data.columns)))
    
    # Apply errors if specified
    if error_type != 'none' and random.random() < error_probability:
        if error_type == 'missing_label':
            # Randomly remove some labels
            for i in range(len(data.index)):
                if random.random() < error_probability:
                    data.index.values[i] = ''
        elif error_type == 'truncated_axis':
            # Will be applied later in plot settings
            pass
        elif error_type == 'color_issues':
            # Will use problematic colors
            pass
        elif error_type == 'overlapping':
            # Will be handled by modifying figure size
            fig.set_figwidth(fig.get_figwidth() * 0.5)
    
    # Override colors if it's a color issue error
    if error_type == 'color_issues' and random.random() < error_probability:
        # Generate similar colors that are hard to distinguish
        base_color = np.random.random(3)
        colors = [np.clip(base_color + np.random.normal(0, 0.1, 3), 0, 1) for _ in range(len(data.columns))]
    
    # Create stacked bar chart
    bottom = np.zeros(len(data.index))
    for i, col in enumerate(data.columns):
        ax.bar(data.index, data[col], bottom=bottom, label=col, color=colors[i], edgecolor='white' if theme == 'dark' else None, linewidth=0.5 if theme in ['dark', 'bmh'] else 0)
        bottom += data[col].values
    
    # Set labels and title with theme-specific styling
    ax.set_title(title, fontsize=14, color=title_color, fontweight='bold')
    ax.set_xlabel(xlabel, fontsize=12, color=label_color)
    ax.set_ylabel(ylabel, fontsize=12, color=label_color)
    
    # Set grid with theme-specific styling
    if include_grid:
        ax.grid(True, linestyle='--', alpha=0.7, color=grid_color)
    else:
        ax.grid(False)
    
    # Apply theme-specific tick styling
    ax.tick_params(axis='both', colors=label_color)
    
    # Apply truncated axis error if specified
    if error_type == 'truncated_axis' and random.random() < error_probability:
        max_value = data.values.sum(axis=1).max()
        ax.set_ylim(0, max_value * 0.8)  # Only show 80% of the data
    
    # Rotate x labels for better readability
    plt.xticks(rotation=45, ha='right', color=label_color)
    
    # Add legend with theme-specific styling
    legend = ax.legend(loc='upper right', framealpha=0.9)
    plt.setp(legend.get_texts(), color=label_color)
    
    # Adjust layout
    plt.tight_layout()
    
    # Convert plot to base64 string
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    
    # Convert data to JSON
    data_json = data.to_dict()
    
    return f"data:image/png;base64,{img_str}", data_json

if __name__ == '__main__':
    app.run(debug=True)
