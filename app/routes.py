import os
from flask import Blueprint, jsonify, render_template, request
from werkzeug.utils import secure_filename
from pathlib import Path
from .config import Config
from .processing.sam_processor import SAMProcessor
from .processing.scene_handler import SceneHandler
from .processing.scene_validator import SceneValidator
from .processing.error_logger import ErrorLogger
from .models import RoomScene, Component, ComponentStatus
from .database import db_manager, db
from flask import abort
from app.validators import validate_component_category, validate_confidence_score
from app.statistics import SceneStatistics
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError

def handle_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except SQLAlchemyError as e:
            return jsonify({
                'error': 'Database error occurred',
                'toast': {'message': 'An error occurred while accessing the database', 'type': 'error'}
            }), 500
        except Exception as e:
            return jsonify({
                'error': str(e),
                'toast': {'message': 'An unexpected error occurred', 'type': 'error'}
            }), 500
    return wrapper

# Blueprints
main_bp = Blueprint('main', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Initialize SAM processor
sam_processor = SAMProcessor(Config.SAM_MODEL_PATH)

# Constants
ROOM_CATEGORIES = ['living_room', 'bedroom', 'dining_room', 'outdoor']

# Main routes (keeping existing functionality)
@main_bp.route('/')
def index():
    # Try to load the model
    success, message = sam_processor.load_model()
    
    response = {
        'status': 'success' if success else 'error',
        'message': message,
        'device': str(sam_processor.device)
    }
    
    return jsonify(response)

# Admin routes
@admin_bp.route('/')
def index():
    """Admin dashboard"""
    return render_template('admin/index.html')

@admin_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """Handle scene upload"""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file provided'}), 400
            
        file = request.files['file']
        category = request.form.get('category')
        
        if not category or category not in ROOM_CATEGORIES:
            return jsonify({'status': 'error', 'message': 'Invalid category'}), 400
        
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
            
        try:
            # Save uploaded file temporarily
            filename = secure_filename(file.filename)
            temp_path = os.path.join('storage', 'temp', filename)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            file.save(temp_path)
            
            # Get current database session
            current_db = db_manager.get_session()
            
            # Process the scene with the file path
            error_logger = ErrorLogger()
            scene_handler = SceneHandler(
                sam_processor, 
                error_logger,
                db_session=current_db,  # Pass the current session
                storage_base='storage'
            )
            
            # Process the scene using the saved file path
            result = scene_handler.process_scene(temp_path, category)
            
            # Clean up temp file
            os.remove(temp_path)
            
            if result.success:
                return jsonify({
                    'status': 'success',
                    'scene_id': result.room_scene_id,
                    'message': 'Scene processed successfully'
                })
            else:
                error_details = {}
                if result.error_details:
                    error_details = {
                        str(k): str(v) for k, v in result.error_details.items()
                    }
                
                return jsonify({
                    'status': 'error',
                    'message': str(result.message),
                    'details': error_details
                }), 400
                
        except Exception as e:
            print(f"Upload error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    return render_template('admin/upload.html', categories=ROOM_CATEGORIES)

@admin_bp.route('/processing')
def processing():
    """View scene processing status and results"""
    db = db_manager.get_session()
    scenes = db.query(RoomScene).order_by(RoomScene.created_at.desc()).all()
    return render_template('admin/processing.html', scenes=scenes)

@admin_bp.route('/scene/<int:scene_id>')
def scene_detail(scene_id):
    db = db_manager.get_session()
    scene = db.get(RoomScene, scene_id)
    
    if not scene:
        return jsonify({'error': 'Scene not found'}), 404
        
    components = db.query(Component).filter_by(room_scene_id=scene_id).all()
    
    # Get statistics for the scene
    stats = SceneStatistics.get_component_stats(db, scene_id)
    validation_stats = SceneStatistics.get_validation_stats(db, scene_id)
    detection_stats = SceneStatistics.get_detection_stats(db, scene_id)
    
    return render_template('admin/scene_detail.html',
        scene=scene,
        components=components,
        basic_stats={
            'total_components': stats['total'],
            'pending_components': stats['pending'],
            'accepted_components': stats['accepted'],
            'rejected_components': stats['rejected'],
            'review_progress': stats['review_progress']
        },
        validation_stats=validation_stats,
        detection_stats=detection_stats,
        component_type_stats=stats['by_type']
    )

@admin_bp.route('/api/scene/<int:scene_id>/components')
def scene_components(scene_id):
    """API endpoint for scene components"""
    db = db_manager.get_session()
    components = db.query(Component).filter_by(room_scene_id=scene_id).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'type': c.component_type,
        'position': c.position_data,
        'file_path': c.file_path,
        'status': c.status.value,
        'confidence_score': c.confidence_score,
        'review_timestamp': c.review_timestamp.isoformat() if c.review_timestamp else None,
        'reviewer_notes': c.reviewer_notes
    } for c in components])

@admin_bp.route('/api/component/<int:component_id>/accept', methods=['POST'])
def accept_component(component_id):
    db = db_manager.get_session()
    component = db.get(Component, component_id)
    
    if not component:
        return jsonify({'error': 'Component not found'}), 404
    
    # Validate component category
    scene = db.get(RoomScene, component.room_scene_id)
    is_valid, message = validate_component_category(
        scene.category,
        component.component_type
    )
    
    if not is_valid:
        return jsonify({'error': message}), 400
        
    notes = request.form.get('notes')
    component.update_status(ComponentStatus.ACCEPTED, notes=notes)
    db.commit()
    
    return render_template('admin/_component_card.html', component=component)

@admin_bp.route('/api/component/<int:component_id>/reject', methods=['POST'])
def reject_component(component_id):
    db = db_manager.get_session()
    component = db.get(Component, component_id)  # Updated from query().get()
    
    if not component:
        return jsonify({'error': 'Component not found'}), 404
    
    notes = request.form.get('notes')
    if not notes:
        return jsonify({'error': 'Rejection notes are required'}), 400
        
    component.update_status(ComponentStatus.REJECTED, notes=notes)
    db.commit()
    
    return render_template('admin/_component_card.html', component=component)

@admin_bp.route('/api/scene/<int:scene_id>/statistics')
@handle_errors
def scene_statistics(scene_id):
    db = db_manager.get_session()
    scene = db.get(RoomScene, scene_id)
    
    if not scene:
        return jsonify({'error': 'Scene not found'}), 404
        
    stats = SceneStatistics.get_component_stats(db, scene_id)
    validation_stats = SceneStatistics.get_validation_stats(db, scene_id)
    detection_stats = SceneStatistics.get_detection_stats(db, scene_id)
    
    return jsonify({
        'basic_stats': {
            'total_components': stats['total'],
            'pending_components': stats['pending'],
            'accepted_components': stats['accepted'],
            'rejected_components': stats['rejected'],
            'review_progress': stats['review_progress']
        },
        'validation_stats': validation_stats,
        'detection_stats': detection_stats,
        'component_type_stats': stats['by_type']
    })

@admin_bp.route('/api/component/<int:component_id>/validate-category', methods=['POST'])
def validate_component_category_endpoint(component_id):
    db = db_manager.get_session()
    component = db.get(Component, component_id)
    
    if not component:
        return jsonify({'error': 'Component not found'}), 404
        
    scene = db.get(RoomScene, component.room_scene_id)
    is_valid, message = validate_component_category(
        scene.category,
        component.component_type
    )
    
    return jsonify({
        'valid': is_valid,
        'message': message,
        'component_id': component_id,
        'room_category' : scene.category,
        'component_type' : component.component_type
    })

@admin_bp.route('/api/component/<int:component_id>/validate', methods=['GET'])
def validate_component(component_id):
    db = db_manager.get_session()
    component = db.get(Component, component_id)
    
    if not component:
        return jsonify({'error': 'Component not found'}), 404
        
    scene = db.get(RoomScene, component.room_scene_id)
    
    # Validate category
    category_valid, category_message = validate_component_category(
        scene.category,
        component.component_type
    )
    
    # Validate confidence score
    confidence_valid, confidence_message = validate_confidence_score(
        component.confidence_score or 0
    )
    
    is_valid = category_valid and confidence_valid
    message = category_message if not category_valid else confidence_message
    
    return render_template('admin/_validation_result.html',
        valid=is_valid,
        message=message,
        component_id=component_id,
        room_category=scene.category,
        validation_details={
            'category': {'valid': category_valid, 'message': category_message},
            'confidence': {'valid': confidence_valid, 'message': confidence_message}
        }
    )

@admin_bp.route('/api/stats/detection-accuracy')
@handle_errors
def detection_accuracy_stats():
    db = db_manager.get_session()
    scene_id = request.args.get('scene_id')
    
    if scene_id:
        stats = SceneStatistics.get_detection_stats(db, int(scene_id))
    else:
        stats = SceneStatistics.get_global_detection_stats(db)
        
    return jsonify(stats)

@admin_bp.route('/api/stats/review-metrics')
@handle_errors
def review_metrics():
    db = db_manager.get_session()
    scene_id = request.args.get('scene_id')
    
    if scene_id:
        stats = SceneStatistics.get_review_metrics(db, int(scene_id))
    else:
        stats = SceneStatistics.get_global_review_metrics(db)
        
    return jsonify(stats)

@admin_bp.route('/api/component/<int:component_id>/status', methods=['POST'])
def update_component_status(component_id):
    db = db_manager.get_session()
    component = db.get(Component, component_id)
    
    if not component:
        return jsonify({
            'error': 'Component not found',
            'toast': {'message': 'Component not found', 'type': 'error'}
        }), 404
    
    new_status = request.json.get('status')
    if new_status not in [s.value for s in ComponentStatus]:
        return jsonify({
            'error': 'Invalid status',
            'toast': {'message': 'Invalid status provided', 'type': 'error'}
        }), 400
    
    component.status = new_status
    db.commit()
    
    return jsonify({
        'status': 'success',
        'toast': {'message': f'Component status updated to {new_status}', 'type': 'success'}
    })

@admin_bp.route('/api/scene/<int:scene_id>/detailed-stats')
def detailed_scene_statistics(scene_id):
    db = db_manager.get_session()
    scene = db.get(RoomScene, scene_id)
    
    if not scene:
        return jsonify({'error': 'Scene not found'}), 404
        
    # Get all statistics
    component_stats = SceneStatistics.get_component_stats(db, scene_id)
    validation_stats = SceneStatistics.get_validation_stats(db, scene_id)
    detection_stats = SceneStatistics.get_detection_stats(db, scene_id)
    review_metrics = SceneStatistics.get_review_metrics(db, scene_id)
    
    return jsonify({
        'basic_stats': {
            'total_components': component_stats['total'],
            'pending_components': component_stats['pending'],
            'accepted_components': component_stats['accepted'],
            'rejected_components': component_stats['rejected'],
            'review_progress': component_stats['review_progress']
        },
        'validation_stats': validation_stats,
        'detection_stats': detection_stats,
        'review_metrics': review_metrics,
        'component_type_stats': component_stats['by_type'],
        'timeline': {
            'created_at': scene.created_at.isoformat(),
            'last_updated': scene.updated_at.isoformat() if scene.updated_at else None,
            'review_completion': scene.review_completion_time.isoformat() if scene.review_completion_time else None
        }
    })

@admin_bp.route('/component/<int:component_id>/card')
def get_component_card(component_id):
    db = db_manager.get_session()  # Add this line
    component = db.get(Component, component_id)
    if not component:
        return jsonify({'error': 'Component not found'}), 404
    return render_template('admin/_component_card.html', component=component)

@admin_bp.route('/debug/db-tables')
def debug_db_tables():
    """Debug endpoint to verify database tables"""
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    return jsonify({
        'tables': tables,
        'has_room_scenes': 'room_scenes' in tables,
        'has_components': 'components' in tables
    })