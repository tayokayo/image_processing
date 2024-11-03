from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy import func
from app.models import Component, ComponentStatus, RoomScene  # Changed from .models
from app.validators import validate_component_category  # Changed from .validators

class SceneStatistics:
    @staticmethod
    def get_detection_stats(db, scene_id: int) -> Dict:
        """Get detailed detection statistics for a scene"""
        components = db.query(Component).filter_by(room_scene_id=scene_id).all()
        
        stats = {
            'confidence_scores': {
                'min': float('inf'),
                'max': float('-inf'),
                'avg': 0,
                'distribution': defaultdict(int)
            },
            'component_types': defaultdict(int),
            'review_times': [],
            'rejection_reasons': defaultdict(int)
        }
        
        total_confidence = 0
        for comp in components:
            # Confidence score stats
            score = comp.confidence_score or 0
            stats['confidence_scores']['min'] = min(stats['confidence_scores']['min'], score)
            stats['confidence_scores']['max'] = max(stats['confidence_scores']['max'], score)
            total_confidence += score
            
            # Bin confidence scores
            bin_key = f"{int(score * 10) * 10}-{int(score * 10) * 10 + 10}"
            stats['confidence_scores']['distribution'][bin_key] += 1
            
            # Component type counts
            stats['component_types'][comp.component_type] += 1
            
            # Review time calculation
            if comp.updated_at and comp.created_at:
                review_time = comp.updated_at - comp.created_at
                stats['review_times'].append(review_time.total_seconds())
            
            # Rejection reasons
            if comp.status == ComponentStatus.REJECTED and comp.reviewer_notes:
                stats['rejection_reasons'][comp.reviewer_notes] += 1
        
        if components:
            stats['confidence_scores']['avg'] = total_confidence / len(components)
            
        return stats
    
    @staticmethod
    def get_component_stats(db, scene_id: int) -> Dict:
        """Get component status statistics"""
        components = db.query(Component).filter_by(room_scene_id=scene_id).all()
        
        stats = {
            'total': len(components),
            'accepted': sum(1 for c in components if c.status == ComponentStatus.ACCEPTED),
            'rejected': sum(1 for c in components if c.status == ComponentStatus.REJECTED),
            'pending': sum(1 for c in components if c.status == ComponentStatus.PENDING),
            'by_type': defaultdict(lambda: {'total': 0, 'accepted': 0, 'rejected': 0, 'pending': 0}),
            'review_progress': 0
        }
        
        for component in components:
            type_stats = stats['by_type'][component.component_type]
            type_stats['total'] += 1
            if component.status == ComponentStatus.ACCEPTED:
                type_stats['accepted'] += 1
            elif component.status == ComponentStatus.REJECTED:
                type_stats['rejected'] += 1
            else:
                type_stats['pending'] += 1
        
        if stats['total'] > 0:
            stats['review_progress'] = round(
                (stats['accepted'] + stats['rejected']) * 100 / stats['total'], 
                2
            )
            
        return stats

    @staticmethod
    def get_validation_stats(db, scene_id: int) -> Dict:
        """Get component validation statistics"""
        scene = db.get(RoomScene, scene_id)
        components = db.query(Component).filter_by(room_scene_id=scene_id).all()
        
        stats = {
            'valid': 0,
            'invalid': 0,
            'by_type': defaultdict(lambda: {'valid': 0, 'invalid': 0}),
            'validation_rate': 0
        }
        
        for component in components:
            is_valid, _ = validate_component_category(
                scene.category,
                component.component_type
            )
            if is_valid:
                stats['valid'] += 1
                stats['by_type'][component.component_type]['valid'] += 1
            else:
                stats['invalid'] += 1
                stats['by_type'][component.component_type]['invalid'] += 1
        
        if components:
            stats['validation_rate'] = round(
                stats['valid'] * 100 / len(components),
                2
            )
            
        return stats
    
    @staticmethod
    def get_global_detection_stats(db) -> Dict:
        """Get global detection statistics across all scenes"""
        components = db.query(Component).all()
        
        stats = {
            'confidence_scores': {
                'min': float('inf'),
                'max': float('-inf'),
                'avg': 0,
                'distribution': defaultdict(int)
            },
            'accuracy_by_category': defaultdict(lambda: {
                'total': 0,
                'correct': 0,
                'incorrect': 0
            })
        }

        for comp in components:
            # Confidence score stats
            score = comp.confidence_score or 0
            stats['confidence_scores']['min'] = min(stats['confidence_scores']['min'], score)
            stats['confidence_scores']['max'] = max(stats['confidence_scores']['max'], score)
            total_confidence += score
            
            # Bin confidence scores (0-10, 10-20, etc.)
            bin_key = f"{int(score * 10) * 10}-{int(score * 10) * 10 + 10}"
            stats['confidence_scores']['distribution'][bin_key] += 1
            
            # Accuracy by category
            scene = db.get(RoomScene, comp.room_scene_id)
            if scene:
                cat_stats = stats['accuracy_by_category'][scene.category]
                cat_stats['total'] += 1
                
                is_valid, _ = validate_component_category(
                    scene.category,
                    comp.component_type
                )
                if is_valid:
                    cat_stats['correct'] += 1
                else:
                    cat_stats['incorrect'] += 1
        
        if components:
            stats['confidence_scores']['avg'] = total_confidence / len(components)
            
        return stats

    @staticmethod
    def get_review_metrics(db, scene_id: int = None) -> Dict:
        """Get review time and efficiency metrics"""
        query = db.query(Component)
        if scene_id:
            query = query.filter_by(room_scene_id=scene_id)
        
        components = query.all()
        
        metrics = {
            'review_times': [],
            'reviews_per_hour': defaultdict(int),
            'accuracy_trend': defaultdict(lambda: {
                'total': 0,
                'correct': 0
            })
        }
        
        for comp in components:
        # Review time calculation
            if comp.updated_at and comp.created_at:
                review_time = comp.updated_at - comp.created_at
                metrics['review_times'].append(review_time.total_seconds())
                
                # Reviews per hour
                hour_key = comp.updated_at.strftime('%Y-%m-%d %H:00')
                metrics['reviews_per_hour'][hour_key] += 1
            
            # Accuracy trend
            if comp.status != ComponentStatus.PENDING:
                date_key = comp.updated_at.strftime('%Y-%m-%d') if comp.updated_at else today.strftime('%Y-%m-%d')
                trend = metrics['accuracy_trend'][date_key]
                trend['total'] += 1
                
                scene = db.get(RoomScene, comp.room_scene_id)
                if scene:
                    is_valid, _ = validate_component_category(
                        scene.category,
                        comp.component_type
                    )
                    if is_valid:
                        trend['correct'] += 1
        
        return metrics