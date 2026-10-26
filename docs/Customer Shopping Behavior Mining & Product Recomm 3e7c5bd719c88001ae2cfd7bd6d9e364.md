# Customer Shopping Behavior Mining & Product Recommendation Using the Instacart Dataset

## 1. Project Overview

This project studies customer shopping behavior using the **Instacart Market Basket Analysis dataset.**

The dataset contains historical grocery orders together with product, aisle, and department information. Because each customer has multiple orders over time, the data can be used to study both individual shopping habits and relationships between products.

The main goal of the project is to discover useful patterns from customer purchase history. The project focuses on three questions:

- What types of shopping behavior can be found among customers?
- Which products are frequently purchased together?
- Which products are likely to be purchased again by a customer?

These questions allow the project to cover several core Data Mining tasks while keeping them connected to the same business problem.

## 2. Dataset Description

The project uses the **Instacart Market Basket Analysis** dataset, which was originally released for a Kaggle competition about predicting which previously purchased products would appear in a customer's next order.

The dataset contains anonymized grocery shopping histories collected across multiple orders. Instead of storing everything in one table, the data is divided into several related files describing orders, products, aisles, departments, and the products contained in each order. The commonly used Kaggle version contains six CSV files and is approximately 713 MB in total.

The main files are:

| File | Description |
| --- | --- |
| `orders.csv` | Basic information about each order and its position in a customer's order history |
| `order_products__prior.csv` | Products included in customers' previous orders |
| `order_products__train.csv` | Products included in the training orders |
| `products.csv` | Product names and their aisle and department identifiers |
| `aisles.csv` | Names of product aisles |
| `departments.csv` | Names of product departments |

The relationships between these files can be summarized as:

```
Customer
   ↓
Order
   ↓
Order–Product
   ↓
Product
   ↓
Aisle
   ↓
Department
```

For each customer, the order history records the sequence of their purchases and includes information such as the day of the week, hour of the day, and time since the previous order. Product-order records also indicate whether an item had been purchased by the same customer before.

This structure makes the dataset suitable for analyzing behavior at several levels:

- **Customer level:** how frequently and consistently customers shop.
- **Order level:** basket size and shopping patterns over time.
- **Product level:** popularity and reorder behavior.
- **Basket level:** products that commonly appear together.
- **Customer-product level:** relationships between individual customers and products they have purchased before.

The original Kaggle task uses these historical interactions to predict which previously purchased products will appear in a customer's next order. For this project, the same data is used more broadly to study customer behavior, product relationships, and reorder patterns.

**Dataset source [here](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis)**

## 3. Data Mining Objectives

The project has three main analysis tasks.

### Customer Behavior Analysis

Customer purchase histories will be summarized into behavioral features such as purchase frequency, basket size, reorder behavior, product diversity, and shopping patterns.

Clustering techniques will then be used to discover groups of customers with similar behavior.

The purpose is to understand whether the dataset contains meaningful customer segments and how these segments differ from each other.

### Product Association Mining

Each order can be treated as a basket of products.

Association rule mining will be used to discover products or product groups that frequently appear together.

The analysis will focus on identifying meaningful relationships between products and explaining how these relationships could support basket recommendation or cross-selling.

### Reorder Prediction

The project will also study whether a product previously purchased by a customer is likely to appear again in a future order.

This task uses information from previous customer-product interactions, order history, product characteristics, and customer behavior.

The prediction task complements the descriptive mining tasks by testing whether the discovered behavioral information can also be used for prediction.

## 4. Expected Outcome

The project should produce a clear view of customer purchasing behavior in the Instacart dataset.

The final analysis will connect three perspectives:

**Customer level:** groups of customers with similar shopping behavior.

**Basket level:** relationships between products that are frequently purchased together.

**Customer-product level:** patterns that help explain whether a customer is likely to purchase a product again.

The results will be evaluated both quantitatively and through interpretation of the discovered patterns.

![mermaid-diagram (1).png](Customer%20Shopping%20Behavior%20Mining%20&%20Product%20Recomm/mermaid-diagram_(1).png)