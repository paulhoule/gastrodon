jupyter nbconvert --to notebook --execute local/RDFContainers.ipynb

jupyter nbconvert --to notebook --execute local/Inference_Over_RDF_Containers.ipynb

jupyter nbconvert --to notebook --execute local/DBpedia_Schema_Queries.ipynb

jupyter nbconvert --to notebook --ExecutePreprocessor.timeout=9999 --execute "remote/Querying DBpedia.ipynb"