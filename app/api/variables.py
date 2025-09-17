from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.core.config import settings
from app.models.database import get_db, Variable
from app.services.qdrant_service import qdrant_service

router = APIRouter()

# Pydantic models for API
class VariableCreate(BaseModel):
    variable_type: str
    parameter_id: Optional[str] = None
    group_parameter: Optional[str] = None
    variable_code: str
    variable_name: str
    des_var_eng: Optional[str] = None
    variable_description: Optional[str] = None
    customer_loan_level: Optional[str] = None
    group_level_1: Optional[str] = None
    group_level_2: Optional[str] = None

class VariableUpdate(BaseModel):
    variable_type: Optional[str] = None
    parameter_id: Optional[str] = None
    group_parameter: Optional[str] = None
    variable_code: Optional[str] = None
    variable_name: Optional[str] = None
    des_var_eng: Optional[str] = None
    variable_description: Optional[str] = None
    customer_loan_level: Optional[str] = None
    group_level_1: Optional[str] = None
    group_level_2: Optional[str] = None

class SemanticSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    score_threshold: Optional[float] = 0.3  # Lower default threshold
    search_type: Optional[str] = None  # "document", "variable", or None for all

# Variables CRUD endpoints
@router.post("/variables")
async def create_variable(
    variable: VariableCreate,
    db = Depends(get_db)
):
    """Create a new variable and add it to semantic search."""
    try:
        # Create variable in database
        db_variable = Variable(
            variable_type=variable.variable_type,
            parameter_id=variable.parameter_id,
            group_parameter=variable.group_parameter,
            variable_code=variable.variable_code,
            variable_name=variable.variable_name,
            des_var_eng=variable.des_var_eng,
            variable_description=variable.variable_description,
            customer_loan_level=variable.customer_loan_level,
            group_level_1=variable.group_level_1,
            group_level_2=variable.group_level_2,
            created_at=datetime.utcnow()
        )
        
        db.add(db_variable)
        db.commit()
        db.refresh(db_variable)
        
        # Add to Qdrant for semantic search
        variable_dict = {
            "variable_type": variable.variable_type,
            "parameter_id": variable.parameter_id,
            "group_parameter": variable.group_parameter,
            "variable_code": variable.variable_code,
            "variable_name": variable.variable_name,
            "des_var_eng": variable.des_var_eng,
            "variable_description": variable.variable_description,
            "customer_loan_level": variable.customer_loan_level,
            "group_level_1": variable.group_level_1,
            "group_level_2": variable.group_level_2
        }
        
        await qdrant_service.add_variables([variable_dict])
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "Variable created successfully",
                "variable_id": db_variable.id,
                "variable_code": db_variable.variable_code,
                "variable_name": db_variable.variable_name,
                "added_to_search": True
            }
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating variable: {str(e)}"
        )

@router.get("/variables")
async def list_variables(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    variable_type: Optional[str] = None,
    group_parameter: Optional[str] = None,
    db = Depends(get_db)
):
    """List variables with optional filtering."""
    try:
        query = db.query(Variable)
        
        if variable_type:
            query = query.filter(Variable.variable_type == variable_type)
        
        if group_parameter:
            query = query.filter(Variable.group_parameter == group_parameter)
        
        variables = query.offset(skip).limit(limit).all()
        
        return [
            {
                "id": var.id,
                "variable_type": var.variable_type,
                "parameter_id": var.parameter_id,
                "group_parameter": var.group_parameter,
                "variable_code": var.variable_code,
                "variable_name": var.variable_name,
                "des_var_eng": var.des_var_eng,
                "variable_description": var.variable_description,
                "customer_loan_level": var.customer_loan_level,
                "group_level_1": var.group_level_1,
                "group_level_2": var.group_level_2,
                "created_at": var.created_at.isoformat(),
                "updated_at": var.updated_at.isoformat()
            }
            for var in variables
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing variables: {str(e)}"
        )

@router.get("/variables/{variable_id}")
async def get_variable(variable_id: int, db = Depends(get_db)):
    """Get a specific variable by ID."""
    variable = db.query(Variable).filter(Variable.id == variable_id).first()
    if not variable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variable not found"
        )
    
    return {
        "id": variable.id,
        "variable_type": variable.variable_type,
        "parameter_id": variable.parameter_id,
        "group_parameter": variable.group_parameter,
        "variable_code": variable.variable_code,
        "variable_name": variable.variable_name,
        "des_var_eng": variable.des_var_eng,
        "variable_description": variable.variable_description,
        "customer_loan_level": variable.customer_loan_level,
        "group_level_1": variable.group_level_1,
        "group_level_2": variable.group_level_2,
        "created_at": variable.created_at.isoformat(),
        "updated_at": variable.updated_at.isoformat()
    }

@router.put("/variables/{variable_id}")
async def update_variable(
    variable_id: int,
    variable_update: VariableUpdate,
    db = Depends(get_db)
):
    """Update a variable."""
    variable = db.query(Variable).filter(Variable.id == variable_id).first()
    if not variable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variable not found"
        )
    
    # Update fields
    update_data = variable_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(variable, field, value)
    
    variable.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Variable updated successfully", "variable_id": variable_id}

@router.delete("/variables/{variable_id}")
async def delete_variable(variable_id: int, db = Depends(get_db)):
    """Delete a variable."""
    variable = db.query(Variable).filter(Variable.id == variable_id).first()
    if not variable:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Variable not found"
        )
    
    db.delete(variable)
    db.commit()
    
    return {"message": "Variable deleted successfully", "variable_id": variable_id}

# Semantic search endpoints
@router.post("/semantic-search")
async def semantic_search(search_request: SemanticSearchRequest):
    """Perform semantic search across documents and variables."""
    try:
        results = await qdrant_service.semantic_search(
            query=search_request.query,
            limit=search_request.limit,
            score_threshold=search_request.score_threshold,
            filter_type=search_request.search_type
        )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "query": search_request.query,
                "results_count": len(results),
                "results": results
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing semantic search: {str(e)}"
        )

@router.get("/search/variables")
async def search_variables_endpoint(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50)
):
    """Search variables using semantic search."""
    try:
        results = await qdrant_service.search_variables(q, limit)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "query": q,
                "search_type": "variables",
                "results_count": len(results),
                "results": results
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching variables: {str(e)}"
        )

@router.get("/search/documents")
async def search_documents_endpoint(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50)
):
    """Search documents using semantic search."""
    try:
        results = await qdrant_service.search_documents(q, limit)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "query": q,
                "search_type": "documents",
                "results_count": len(results),
                "results": results
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching documents: {str(e)}"
        )

@router.post("/variables/bulk-create")
async def bulk_create_variables(
    variables: List[VariableCreate],
    db = Depends(get_db)
):
    """Create multiple variables at once and add them to semantic search."""
    try:
        db_variables = []
        variable_dicts = []
        
        for variable in variables:
            db_variable = Variable(
                variable_type=variable.variable_type,
                parameter_id=variable.parameter_id,
                group_parameter=variable.group_parameter,
                variable_code=variable.variable_code,
                variable_name=variable.variable_name,
                des_var_eng=variable.des_var_eng,
                variable_description=variable.variable_description,
                customer_loan_level=variable.customer_loan_level,
                group_level_1=variable.group_level_1,
                group_level_2=variable.group_level_2,
                created_at=datetime.utcnow()
            )
            
            db_variables.append(db_variable)
            
            variable_dicts.append({
                "variable_type": variable.variable_type,
                "parameter_id": variable.parameter_id,
                "group_parameter": variable.group_parameter,
                "variable_code": variable.variable_code,
                "variable_name": variable.variable_name,
                "des_var_eng": variable.des_var_eng,
                "variable_description": variable.variable_description,
                "customer_loan_level": variable.customer_loan_level,
                "group_level_1": variable.group_level_1,
                "group_level_2": variable.group_level_2
            })
        
        # Add to database
        db.add_all(db_variables)
        db.commit()
        
        # Add to Qdrant for semantic search
        await qdrant_service.add_variables(variable_dicts)
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": f"Successfully created {len(variables)} variables",
                "variables_created": len(db_variables),
                "added_to_search": True
            }
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating variables: {str(e)}"
        )

@router.get("/qdrant/info")
async def get_qdrant_info():
    """Get information about the Qdrant collection."""
    try:
        info = qdrant_service.get_collection_info()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "qdrant_info": info,
                "collection_name": qdrant_service.collection_name
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting Qdrant info: {str(e)}"
        )

@router.post("/variables/sync-to-qdrant")
async def sync_variables_to_qdrant():
    """Sync all variables from database to Qdrant (auto-detects duplicates)."""
    try:
        result = await qdrant_service.sync_variables_from_database()
        
        if result["success"]:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": result["message"],
                    "sync_result": result
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": result["message"],
                    "sync_result": result
                }
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing variables to Qdrant: {str(e)}"
        )

@router.post("/variables/force-resync-to-qdrant")
async def force_resync_variables_to_qdrant():
    """Force resync all variables to Qdrant (removes existing ones first)."""
    try:
        result = await qdrant_service.force_resync_all_variables()
        
        if result["success"]:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": result["message"],
                    "sync_result": result
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": result["message"],
                    "sync_result": result
                }
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error force resyncing variables to Qdrant: {str(e)}"
        )

@router.get("/debug/qdrant-search")
async def debug_qdrant_search(
    q: str = Query(..., description="Search query"),
    threshold: float = Query(0.1, description="Score threshold")
):
    """Debug endpoint to test Qdrant search with different thresholds."""
    try:
        # Test different search configurations
        results = []
        
        # 1. Search with very low threshold, no filter
        result1 = await qdrant_service.semantic_search(q, limit=10, score_threshold=threshold, filter_type=None)
        results.append({
            "search_config": "No filter, low threshold",
            "threshold": threshold,
            "filter": None,
            "count": len(result1),
            "results": result1[:3]  # Show first 3 for brevity
        })
        
        # 2. Search with filter for variables
        result2 = await qdrant_service.semantic_search(q, limit=10, score_threshold=threshold, filter_type="variable")
        results.append({
            "search_config": "With variable filter, low threshold", 
            "threshold": threshold,
            "filter": "variable",
            "count": len(result2),
            "results": result2[:3]
        })
        
        # 3. Get collection info
        collection_info = qdrant_service.get_collection_info()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "query": q,
                "collection_info": collection_info,
                "search_tests": results,
                "recommendations": [
                    "If no results found, try lowering score_threshold to 0.1 or 0.3",
                    "Check if data has correct 'type' field set to 'variable'",
                    "Use the /debug/qdrant-search endpoint to test different configurations"
                ]
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error debugging Qdrant search: {str(e)}"
        )