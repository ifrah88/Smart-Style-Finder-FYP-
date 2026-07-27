# Smart-Style-Finder-FYP- 
## AI-Powered Fashion Search & Recommendation System

Smart Style Finder is an AI-based fashion discovery platform that allows users to search clothing products using either images or text descriptions. The system uses deep learning and computer vision techniques to understand clothing style, colour, and visual features, then recommends the most similar products with complete details such as title, brand, colour, fabric, and price.

## Functionality

The platform provides two main search methods:

Image-Based Search: 
Users can upload a clothing image, and the system analyzes the image to find visually similar products from the database. The uploaded image is converted into a feature representation using FashionCLIP, and similar products are retrieved based on visual similarity.

Text-Based Search:  
Users can search using natural language descriptions such as "baby pink embroidered dress" or "black printed lawn shirt". The text query is converted into an embedding using the FashionCLIP text encoder, allowing the system to understand the meaning of the query and retrieve matching products.

Colour-Aware Recommendation: 
To improve recommendation accuracy, Smart Style Finder includes a colour-aware ranking mechanism. Traditional image retrieval models can identify similar styles but may return products with incorrect colours. To overcome this limitation, the system combines FashionCLIP similarity with actual garment colour analysis.

The system extracts dominant colours from clothing images using segmentation, CIELAB colour space conversion, and K-means clustering. The final recommendations are re-ranked based on both visual similarity and colour similarity, resulting in more accurate fashion matches.

## Backend Workflow

The backend consists of an AI retrieval pipeline responsible for processing product data, generating embeddings, analyzing colours, and returning relevant recommendations.

Dataset Processing:
Clothing products were collected from Sapphire Online. The images were cleaned, segmented to remove background information, and paired with product metadata including title, brand, colour, fabric, and price.

Dataset details:
- 3,494 raw images
- 2,261 segmented images
- 2,263 cleaned products used for the AI model

Image Feature Extraction: 
Each product image is processed using FashionCLIP to generate a 512-dimensional embedding vector. These embeddings represent the visual features of clothing items and are stored for similarity search.

Workflow:

Product Image → FashionCLIP Encoder → Image Embedding → Similarity Database

When a user uploads an image, the same process is applied to the query image, and the system retrieves products with similar visual features.

Colour Analysis Module:  
To improve colour matching, the system performs additional colour analysis on segmented clothing images.

Process:

Segmented Image → Garment Pixel Extraction → RGB to CIELAB Conversion → K-Means Clustering → Dominant Colour Palette

The extracted colour information helps the system identify accurate garment colours and improves the ranking of recommended products.

Recommendation Pipeline:

User Image/Text Query  
↓  
FashionCLIP Encoding  
↓  
Retrieve Similar Products  
↓  
Colour Similarity Re-ranking  
↓  
Return Top-5 Recommendations

The final ranking combines FashionCLIP semantic similarity with colour similarity to provide recommendations that match both the style and appearance of the query.

## AI Models Used

**FashionCLIP Retrieval Model**
- Generates image and text embeddings
- Supports image-based and text-based search
- Retrieves visually and semantically similar fashion products

ResNet50 Multi-task CNN Model

A ResNet50-based CNN model was trained for clothing attribute prediction.

The model predicts:
- Clothing colour categories
- Design categories:
  - Embroidered
  - Printed
  - Solid
  - Jacquard

Model performance:
- Colour Classification Accuracy: 58.2%
- Design Classification Accuracy: 69.7%

## Technologies Used

Artificial Intelligence & Machine Learning
- FashionCLIP
- ResNet50
- TensorFlow
- PyTorch
- FAISS
- Scikit-learn

Computer Vision
- OpenCV
- PIL
- CIELAB Colour Space
- K-Means Clustering

Backend Development
- Python
- Flask/FastAPI integration
