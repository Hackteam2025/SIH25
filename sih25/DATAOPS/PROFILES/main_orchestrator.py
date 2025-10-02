#!/usr/bin/env python3
"""
Argo Data Pipeline Orchestration with Prefect
Orchestrates the complete pipeline: Schema → Validation → Preprocessing → Export
"""

from pathlib import Path
from typing import Dict, Any
import asyncio

from prefect import flow, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

# Import our modular tasks with proper package paths
from sih25.DATAOPS.PROFILES.step3_schema_explorer import explore_argo_schema
from sih25.DATAOPS.PROFILES.step4_data_validator import validate_argo_data
from sih25.DATAOPS.PROFILES.step5_data_preprocessor import preprocess_argo_data
from sih25.DATAOPS.PROFILES.step6_data_exporter_parquet import export_to_parquet

# Import DATA LOADER
try:
    from sih25.LOADER.data_loader import load_parquet_to_postgres
    LOADER_AVAILABLE = True
except ImportError as e:
    LOADER_AVAILABLE = False
    print(f"Warning: Could not import LOADER module: {e}")


@flow(
    name="argo-data-pipeline",
    description="Complete Argo NetCDF to Parquet processing pipeline with optional database loading",
    task_runner=ConcurrentTaskRunner(),
)
async def argo_data_pipeline(
    nc_file_path: str,
    output_dir: str = "output",
    skip_validation_errors: bool = False,
    load_to_database: bool = False,
    create_db_tables: bool = True,
    deduplication_strategy: str = "upsert"
) -> Dict[str, Any]:
    """
    Complete Argo data processing pipeline

    Args:
        nc_file_path: Path to Argo NetCDF file
        output_dir: Output directory for processed files
        skip_validation_errors: Continue processing even with validation errors
        load_to_database: Whether to load data into PostgreSQL database
        create_db_tables: Whether to create database tables if they don't exist
        deduplication_strategy: "upsert" or "ignore" for handling database duplicates

    Returns:
        Dictionary with pipeline results and file paths
    """
    logger = get_run_logger()
    file_name = Path(nc_file_path).name
    
    logger.info(f"Starting Argo pipeline for: {file_name}")
    
    pipeline_results = {
        "input_file": nc_file_path,
        "file_name": file_name,
        "status": "started",
        "steps_completed": [],
        "output_files": {},
        "errors": []
    }
    
    try:
        # Step 3: Schema Exploration
        logger.info("Step 3: Starting schema exploration...")
        schema_info = explore_argo_schema(nc_file_path)
        pipeline_results["schema_info"] = schema_info
        pipeline_results["steps_completed"].append("schema_exploration")
        
        logger.info(f"Schema exploration complete - File type: {schema_info.get('file_type', 'unknown')}")
        
        # Step 4: Data Validation
        logger.info("Step 4: Starting data validation...")
        validation_result = validate_argo_data(nc_file_path, schema_info)
        pipeline_results["validation_result"] = validation_result.dict()
        pipeline_results["steps_completed"].append("validation")
        
        if not validation_result.is_valid:
            error_msg = f"Validation failed: {len(validation_result.validation_errors)} errors found"
            logger.error(error_msg)
            pipeline_results["errors"].append(error_msg)
            
            if not skip_validation_errors:
                pipeline_results["status"] = "failed_validation"
                return pipeline_results
            else:
                logger.warning("Continuing despite validation errors due to skip_validation_errors=True")
        
        logger.info(f"Validation complete - Valid: {validation_result.is_valid}, Records: {validation_result.valid_records}")

        # Step 5: Data Preprocessing
        logger.info("Step 5: Starting data preprocessing...")
        try:
            processed_df = preprocess_argo_data(nc_file_path, validation_result.dict())
            
            if processed_df.empty:
                error_msg = "No valid data found after preprocessing"
                logger.error(error_msg)
                pipeline_results["errors"].append(error_msg)
                pipeline_results["status"] = "failed_preprocessing"
                return pipeline_results
            
            pipeline_results["processed_records"] = len(processed_df)
            pipeline_results["steps_completed"].append("preprocessing")
            
            logger.info(f"Preprocessing complete - Records: {len(processed_df)}")
            
        except Exception as e:
            error_msg = f"Preprocessing failed: {str(e)}"
            logger.error(error_msg)
            pipeline_results["errors"].append(error_msg)
            pipeline_results["status"] = "failed_preprocessing"
            return pipeline_results
        
        # Step 6: Export to Parquet
        logger.info("Step 6: Starting export to Parquet...")
        try:
            file_prefix = Path(nc_file_path).stem
            export_results = export_to_parquet(
                processed_df,
                output_dir,
                file_prefix=file_prefix,
                include_metadata=True
            )

            pipeline_results["output_files"] = export_results
            pipeline_results["steps_completed"].append("export")

            logger.info(f"Export complete - Files created: {len(export_results)}")

        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            logger.error(error_msg)
            pipeline_results["errors"].append(error_msg)
            pipeline_results["status"] = "failed_export"
            return pipeline_results

        # Step 7: Load to Database (Optional)
        if load_to_database:
            if not LOADER_AVAILABLE:
                error_msg = "Database loading requested but LOADER module not available"
                logger.error(error_msg)
                pipeline_results["errors"].append(error_msg)
                pipeline_results["status"] = "failed_loader_unavailable"
                return pipeline_results

            logger.info("Step 7: Starting database loading...")
            try:
                db_results = await load_parquet_to_postgres(
                    parquet_files_dir=output_dir,
                    file_prefix=file_prefix,
                    create_tables=create_db_tables,
                    deduplication_strategy=deduplication_strategy
                )

                pipeline_results["database_results"] = db_results
                pipeline_results["steps_completed"].append("database_loading")

                logger.info(f"Database loading complete - Records loaded: {db_results.get('observations_processed', 0)}")

            except Exception as e:
                error_msg = f"Database loading failed: {str(e)}"
                logger.error(error_msg)
                pipeline_results["errors"].append(error_msg)
                pipeline_results["status"] = "failed_database_loading"
                return pipeline_results

        # Pipeline completed successfully
        pipeline_results["status"] = "completed"
        logger.info(f"Pipeline completed successfully for {file_name}")

        return pipeline_results
        
    except Exception as e:
        error_msg = f"Pipeline failed with unexpected error: {str(e)}"
        logger.error(error_msg)
        pipeline_results["errors"].append(error_msg)
        pipeline_results["status"] = "failed_unexpected"
        return pipeline_results


@flow(
    name="argo-batch-pipeline",
    description="Process multiple Argo files in batch",
)
async def argo_batch_pipeline(
    nc_files: list,
    output_dir: str = "output",
    max_concurrent: int = 3,
    skip_validation_errors: bool = False,
    load_to_database: bool = False,
    create_db_tables: bool = True,
    deduplication_strategy: str = "upsert"
) -> Dict[str, Any]:
    """
    Process multiple Argo NetCDF files in batch

    Args:
        nc_files: List of NetCDF file paths
        output_dir: Output directory
        max_concurrent: Maximum concurrent file processing
        skip_validation_errors: Continue processing files with validation errors
        load_to_database: Whether to load data into PostgreSQL database
        create_db_tables: Whether to create database tables if they don't exist
        deduplication_strategy: "upsert" or "ignore" for handling database duplicates

    Returns:
        Batch processing results
    """
    logger = get_run_logger()
    logger.info(f"Starting batch processing of {len(nc_files)} files")
    
    batch_results = {
        "total_files": len(nc_files),
        "processed_files": [],
        "failed_files": [],
        "summary": {}
    }
    
    # Process files with concurrency limit
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_single_file(file_path):
        async with semaphore:
            try:
                result = await argo_data_pipeline(
                    file_path,
                    output_dir,
                    skip_validation_errors,
                    load_to_database,
                    create_db_tables,
                    deduplication_strategy
                )
                return file_path, result
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                return file_path, {"status": "failed", "error": str(e)}
    
    # Execute all file processing tasks
    tasks = [process_single_file(file_path) for file_path in nc_files]
    results = await asyncio.gather(*tasks)
    
    # Collect results
    successful_count = 0
    failed_count = 0
    
    for file_path, result in results:
        if result.get("status") == "completed":
            batch_results["processed_files"].append({
                "file": file_path,
                "result": result
            })
            successful_count += 1
        else:
            batch_results["failed_files"].append({
                "file": file_path,
                "result": result
            })
            failed_count += 1
    
    batch_results["summary"] = {
        "successful": successful_count,
        "failed": failed_count,
        "success_rate": successful_count / len(nc_files) if nc_files else 0
    }
    
    logger.info(f"Batch processing complete: {successful_count}/{len(nc_files)} files processed successfully")
    
    return batch_results


# CLI interface
if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description="Argo Data Processing Pipeline")
    parser.add_argument("input", help="NetCDF file or directory containing NetCDF files")
    parser.add_argument("-o", "--output", default="output", help="Output directory")
    parser.add_argument("--batch", action="store_true", help="Process multiple files in directory")
    parser.add_argument("--max-concurrent", type=int, default=3, help="Max concurrent files in batch mode")
    parser.add_argument("--skip-validation", action="store_true", help="Skip validation errors")
    parser.add_argument("--save-results", action="store_true", help="Save pipeline results to JSON")

    # Database loading options
    parser.add_argument("--load-to-database", action="store_true", help="Load processed data into PostgreSQL database")
    parser.add_argument("--no-create-tables", action="store_true", help="Don't create database tables (assume they exist)")
    parser.add_argument("--dedup-strategy", choices=["upsert", "ignore"], default="upsert",
                       help="Deduplication strategy for database loading")
    
    args = parser.parse_args()
    
    if args.batch:
        # Batch processing mode
        input_path = Path(args.input)
        if not input_path.is_dir():
            print(f"Error: {input_path} is not a directory")
            exit(1)
        
        nc_files = list(input_path.glob("*.nc"))
        if not nc_files:
            print(f"No NetCDF files found in {input_path}")
            exit(1)
        
        print(f"Found {len(nc_files)} NetCDF files to process")
        
        # Run batch pipeline
        results = asyncio.run(argo_batch_pipeline(
            [str(f) for f in nc_files],
            args.output,
            args.max_concurrent,
            args.skip_validation,
            args.load_to_database,
            not args.no_create_tables,
            args.dedup_strategy
        ))
        
        if args.save_results:
            results_file = Path(args.output) / "batch_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Batch results saved to: {results_file}")
        
        print(f"\nBatch Summary:")
        print(f"  Total files: {results['total_files']}")
        print(f"  Successful: {results['summary']['successful']}")
        print(f"  Failed: {results['summary']['failed']}")
        print(f"  Success rate: {results['summary']['success_rate']:.1%}")
        
    else:
        # Single file processing mode
        if not Path(args.input).exists():
            print(f"Error: File {args.input} does not exist")
            exit(1)
        
        print(f"Processing single file: {args.input}")
        
        # Run single file pipeline
        results = asyncio.run(argo_data_pipeline(
            args.input,
            args.output,
            args.skip_validation,
            args.load_to_database,
            not args.no_create_tables,
            args.dedup_strategy
        ))
        
        if args.save_results:
            results_file = Path(args.output) / f"{Path(args.input).stem}_pipeline_results.json"
            Path(args.output).mkdir(parents=True, exist_ok=True)
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Pipeline results saved to: {results_file}")
        
        print(f"\nPipeline Summary:")
        print(f"  Status: {results['status']}")
        print(f"  Steps completed: {', '.join(results['steps_completed'])}")
        if results.get('processed_records'):
            print(f"  Records processed: {results['processed_records']}")
        if results.get('output_files'):
            print(f"  Output files created: {len(results['output_files'])}")
            for file_type, path in results['output_files'].items():
                print(f"    - {file_type}: {path}")
        if results.get('errors'):
            print(f"  Errors: {len(results['errors'])}")
            for error in results['errors']:
                print(f"    - {error}")