from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, Range
import uuid
from typing import List, Dict, Any, Optional
from app.core.config import settings
import asyncio
import logging

# Try to import sentence transformers, but make it optional
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ SentenceTransformers not available: {str(e)}")
    print("🔧 To fix this, run: pip install sentence-transformers==2.2.2 huggingface_hub==0.19.4")
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Try to import PayloadSchemaType for index creation
try:
    from qdrant_client.models import PayloadSchemaType
    PAYLOAD_SCHEMA_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ PayloadSchemaType not available: {str(e)}")
    PAYLOAD_SCHEMA_AVAILABLE = False

logger = logging.getLogger(__name__)

class QdrantService:
    """Service for semantic search using Qdrant vector database."""
    
    def __init__(self):
        self.client = None
        self.embedding_model = None
        self.collection_name = settings.qdrant_collection_name
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Qdrant client and embedding model."""
        try:
            print(f"🔧 Initializing Qdrant client...")
            print(f"🔑 API Key configured: {'Yes' if settings.qdrant_api_key and len(settings.qdrant_api_key) > 10 else 'No'}")
            print(f"🌐 URL: {settings.qdrant_url}")
            print(f"📂 Collection: {self.collection_name}")
            
            if not settings.qdrant_api_key:
                print("⚠️ Qdrant API key not configured. Semantic search will be disabled.")
                return
            
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                print("⚠️ SentenceTransformers not available. Semantic search will be disabled.")
                return
            
            # Initialize Qdrant client
            self.client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
            )
            
            # Initialize embedding model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            print(f"✅ Qdrant client initialized successfully")
            
            # Ensure collection exists
            self._ensure_collection_exists()
            
        except Exception as e:
            print(f"❌ Failed to initialize Qdrant client: {str(e)}")
            logger.error(f"Qdrant initialization error: {str(e)}")
            # Don't raise here to allow app to start without Qdrant
    
    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist."""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]
            
            if self.collection_name not in collection_names:
                print(f"📂 Creating collection: {self.collection_name}")
                
                # Create collection with vector configuration
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # all-MiniLM-L6-v2 produces 384-dimensional vectors
                        distance=Distance.COSINE
                    )
                )
                print(f"✅ Collection '{self.collection_name}' created successfully")
                
                # Create indexes for filtering
                self._create_payload_indexes()
            else:
                print(f"✅ Collection '{self.collection_name}' already exists")
                # Try to create indexes in case they don't exist
                self._create_payload_indexes()
                
        except Exception as e:
            print(f"❌ Error ensuring collection exists: {str(e)}")
            logger.error(f"Collection creation error: {str(e)}")
    
    def _create_payload_indexes(self):
        """Create payload indexes for filtering."""
        if not PAYLOAD_SCHEMA_AVAILABLE:
            print("⚠️ PayloadSchemaType not available, skipping index creation")
            return
            
        try:
            # Create index for 'type' field
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="type",
                field_schema=PayloadSchemaType.KEYWORD
            )
            print(f"✅ Created index for 'type' field")
            
            # Create index for 'variable_code' field
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="variable_code",
                field_schema=PayloadSchemaType.KEYWORD
            )
            print(f"✅ Created index for 'variable_code' field")
            
            # Create index for 'document_id' field  
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="document_id",
                field_schema=PayloadSchemaType.KEYWORD
            )
            print(f"✅ Created index for 'document_id' field")
            
        except Exception as e:
            # Indexes might already exist, which is fine
            if "already exists" in str(e).lower():
                print(f"⚠️ Indexes already exist (this is fine)")
            else:
                print(f"⚠️ Error creating payload indexes: {str(e)}")
                logger.warning(f"Payload index creation error: {str(e)}")
    
    async def add_document(self, document_id: str, text: str, metadata: Dict[str, Any] = None) -> bool:
        """Add a document to the vector database."""
        try:
            if not self.client or not self.embedding_model or not SENTENCE_TRANSFORMERS_AVAILABLE:
                print("⚠️ Qdrant client or embedding model not available - skipping document indexing")
                return False
            
            # Generate embedding
            embedding = self.embedding_model.encode(text).tolist()
            
            # Prepare metadata
            payload = {
                "document_id": document_id,
                "text": text[:1000],  # Store first 1000 chars for context
                "text_length": len(text),
                **(metadata or {})
            }
            
            # Create point
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload
            )
            
            # Upsert point to collection
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            print(f"✅ Document {document_id} added to Qdrant successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error adding document to Qdrant: {str(e)}")
            logger.error(f"Document addition error: {str(e)}")
            return False
    
    async def add_variables(self, variables: List[Dict[str, Any]]) -> bool:
        """Add variable definitions to the vector database for semantic search."""
        try:
            if not self.client or not self.embedding_model or not SENTENCE_TRANSFORMERS_AVAILABLE:
                print("⚠️ Qdrant client or embedding model not available - skipping variable indexing")
                return False
            
            points = []
            for var in variables:
                # Create searchable text from variable information
                searchable_text = f"{var.get('variable_name', '')} {var.get('variable_description', '')} {var.get('des_var_eng', '')}"
                
                if not searchable_text.strip():
                    continue
                
                # Generate embedding
                embedding = self.embedding_model.encode(searchable_text).tolist()
                
                # Prepare metadata
                payload = {
                    "type": "variable",
                    "variable_code": var.get('variable_code', ''),
                    "variable_name": var.get('variable_name', ''),
                    "variable_description": var.get('variable_description', ''),
                    "des_var_eng": var.get('des_var_eng', ''),
                    "variable_type": var.get('variable_type', ''),
                    "group_parameter": var.get('group_parameter', ''),
                    "customer_loan_level": var.get('customer_loan_level', ''),
                    "group_level_1": var.get('group_level_1', ''),
                    "group_level_2": var.get('group_level_2', ''),
                    "searchable_text": searchable_text
                }
                
                # Create point
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload=payload
                )
                points.append(point)
            
            if points:
                # Upsert points to collection
                operation_info = self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                print(f"✅ {len(points)} variables added to Qdrant successfully")
                return True
            else:
                print("⚠️ No valid variables to add to Qdrant")
                return False
            
        except Exception as e:
            print(f"❌ Error adding variables to Qdrant: {str(e)}")
            logger.error(f"Variables addition error: {str(e)}")
            return False
    
    async def semantic_search(self, query: str, limit: int = 10, score_threshold: float = 0.3, filter_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Perform semantic search across documents and variables."""
        try:
            if not self.client or not self.embedding_model or not SENTENCE_TRANSFORMERS_AVAILABLE:
                print("⚠️ Qdrant client or embedding model not available - returning empty results")
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            print(f"🔍 Searching for: '{query}' with threshold: {score_threshold}, filter: {filter_type}")
            
            # Try search with filter first
            search_results = []
            if filter_type:
                try:
                    # Prepare filter
                    search_filter = Filter(
                        must=[
                            FieldCondition(
                                key="type",
                                match={"value": filter_type}
                            )
                        ]
                    )
                    # Perform filtered search
                    search_results = self.client.search(
                        collection_name=self.collection_name,
                        query_vector=query_embedding,
                        limit=limit,
                        score_threshold=score_threshold,
                        query_filter=search_filter
                    )
                    print(f"✅ Filtered search completed: {len(search_results)} results")
                    
                except Exception as filter_error:
                    print(f"⚠️ Filtered search failed: {str(filter_error)}")
                    if "Index required" in str(filter_error):
                        print("💡 Index not found for 'type' field - falling back to unfiltered search")
                    search_results = []
            
            # If no results with filter or no filter requested, try without filter
            if len(search_results) == 0:
                print(f"🔍 Performing search without filter...")
                search_results_no_filter = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_embedding,
                    limit=limit,
                    score_threshold=score_threshold,
                    query_filter=None
                )
                print(f"✅ Unfiltered search completed: {len(search_results_no_filter)} results")
                
                # Manual filtering if needed
                if filter_type:
                    search_results = []
                    for result in search_results_no_filter:
                        if result.payload and result.payload.get("type") == filter_type:
                            search_results.append(result)
                    print(f"� Manual filtering applied: {len(search_results)} results match type '{filter_type}'")
                else:
                    search_results = search_results_no_filter
            
            # Format results
            results = []
            for result in search_results:
                results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                })
                if result.payload:
                    print(f"� Result: ID={result.id}, Score={result.score:.4f}, Type={result.payload.get('type', 'unknown')}")
            
            print(f"🎯 Found {len(results)} semantic search results for query: '{query}'")
            return results
            
        except Exception as e:
            print(f"❌ Error performing semantic search: {str(e)}")
            logger.error(f"Semantic search error: {str(e)}")
            return []
    
    async def search_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search specifically in documents."""
        return await self.semantic_search(query, limit, filter_type="document")
    
    async def search_variables(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search specifically in variables."""
        return await self.semantic_search(query, limit, filter_type="variable")
    
    async def get_similar_variables(self, variable_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find variables similar to a given variable name."""
        return await self.search_variables(variable_name, limit)
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        try:
            if not self.client:
                return {"error": "Qdrant client not initialized"}
            
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "name": collection_info.config.params.vectors.size,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def sync_variables_from_database(self) -> Dict[str, Any]:
        """Auto-sync all variables from database to Qdrant, avoiding duplicates."""
        try:
            if not self.client or not self.embedding_model or not SENTENCE_TRANSFORMERS_AVAILABLE:
                return {
                    "success": False,
                    "message": "Qdrant client or embedding model not available",
                    "synced_count": 0,
                    "skipped_count": 0,
                    "total_db_variables": 0
                }
            
            print("🔄 Starting auto-sync of variables to Qdrant...")
            
            # Import here to avoid circular imports
            from app.models.database import SessionLocal, Variable
            
            db = SessionLocal()
            synced_count = 0
            skipped_count = 0
            
            try:
                # Get all variables from database
                db_variables = db.query(Variable).all()
                total_db_variables = len(db_variables)
                
                print(f"📊 Found {total_db_variables} variables in database")
                
                if total_db_variables == 0:
                    return {
                        "success": True,
                        "message": "No variables found in database",
                        "synced_count": 0,
                        "skipped_count": 0,
                        "total_db_variables": 0
                    }
                
                # Get existing variable codes from Qdrant
                existing_variable_codes = await self._get_existing_variable_codes()
                print(f"📋 Found {len(existing_variable_codes)} existing variables in Qdrant")
                
                # Prepare variables to sync
                variables_to_sync = []
                
                for db_var in db_variables:
                    if db_var.variable_code in existing_variable_codes:
                        skipped_count += 1
                        # print(f"⏭️ Skipping {db_var.variable_code} - already exists in Qdrant")
                        continue
                    
                    # Convert database variable to dict for Qdrant
                    var_dict = {
                        "variable_type": db_var.variable_type,
                        "parameter_id": db_var.parameter_id,
                        "group_parameter": db_var.group_parameter,
                        "variable_code": db_var.variable_code,
                        "variable_name": db_var.variable_name,
                        "des_var_eng": db_var.des_var_eng,
                        "variable_description": db_var.variable_description,
                        "customer_loan_level": db_var.customer_loan_level,
                        "group_level_1": db_var.group_level_1,
                        "group_level_2": db_var.group_level_2
                    }
                    variables_to_sync.append(var_dict)
                
                # Sync new variables to Qdrant
                if variables_to_sync:
                    success = await self.add_variables(variables_to_sync)
                    if success:
                        synced_count = len(variables_to_sync)
                        print(f"✅ Successfully synced {synced_count} new variables to Qdrant")
                    else:
                        print("❌ Failed to sync variables to Qdrant")
                else:
                    print("✅ All variables are already synced to Qdrant")
                
                return {
                    "success": True,
                    "message": f"Auto-sync completed: {synced_count} added, {skipped_count} skipped",
                    "synced_count": synced_count,
                    "skipped_count": skipped_count,
                    "total_db_variables": total_db_variables
                }
                
            finally:
                db.close()
                
        except Exception as e:
            error_msg = f"Error during auto-sync: {str(e)}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "synced_count": 0,
                "skipped_count": 0,
                "total_db_variables": 0
            }
    
    async def _get_existing_variable_codes(self) -> set:
        """Get all existing variable codes from Qdrant collection."""
        try:
            if not self.client:
                return set()
            
            # Search for all variable type points
            search_results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="type",
                            match={"value": "variable"}
                        )
                    ]
                ),
                limit=10000  # Adjust based on expected number of variables
            )
            
            variable_codes = set()
            for point in search_results[0]:  # scroll returns (points, next_page_offset)
                if point.payload and "variable_code" in point.payload:
                    variable_codes.add(point.payload["variable_code"])
            
            return variable_codes
            
        except Exception as e:
            print(f"⚠️ Error getting existing variable codes: {str(e)}")
            return set()
    
    async def force_resync_all_variables(self) -> Dict[str, Any]:
        """Force resync all variables, removing existing ones first."""
        try:
            if not self.client or not self.embedding_model or not SENTENCE_TRANSFORMERS_AVAILABLE:
                return {
                    "success": False,
                    "message": "Qdrant client or embedding model not available"
                }
            
            print("🔄 Starting force resync of all variables...")
            
            # Delete existing variable points
            await self._delete_all_variables_from_qdrant()
            
            # Sync all variables from database
            result = await self.sync_variables_from_database()
            result["message"] = f"Force resync completed: {result['synced_count']} variables added"
            
            return result
            
        except Exception as e:
            error_msg = f"Error during force resync: {str(e)}"
            print(f"❌ {error_msg}")
            return {"success": False, "message": error_msg}
    
    async def _delete_all_variables_from_qdrant(self):
        """Delete all variable type points from Qdrant."""
        try:
            if not self.client:
                return
            
            # Get all variable points
            search_results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="type",
                            match={"value": "variable"}
                        )
                    ]
                ),
                limit=10000
            )
            
            # Delete points by IDs
            point_ids = [point.id for point in search_results[0]]
            if point_ids:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids
                )
                print(f"🗑️ Deleted {len(point_ids)} existing variable points from Qdrant")
            
        except Exception as e:
            print(f"⚠️ Error deleting variables from Qdrant: {str(e)}")
    
    def close(self):
        """Clean up resources."""
        if self.client:
            try:
                self.client.close()
                print("✅ Qdrant client closed successfully")
            except Exception as e:
                print(f"❌ Error closing Qdrant client: {str(e)}")

# Global instance
qdrant_service = QdrantService()