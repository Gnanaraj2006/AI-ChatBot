# Machine Learning & Deep Learning: Exam Essentials

## 1. Core Paradigms of Machine Learning
Machine Learning algorithms learn patterns from data to perform tasks without being explicitly programmed.

- **Supervised Learning**: Model learns from labeled training data $(X, y)$. Examples: Linear Regression, Logistic Regression, Support Vector Machines (SVM), Random Forests, Neural Networks.
- **Unsupervised Learning**: Model discovers hidden patterns or clusters in unlabeled data $X$. Examples: K-Means Clustering, Principal Component Analysis (PCA), Autoencoders, Gaussian Mixture Models (GMM).
- **Reinforcement Learning**: An agent interacts with an environment through states, actions, and rewards to learn an optimal policy $\pi(s)$. Key equations include the Bellman Equation.

## 2. The Bias-Variance Tradeoff & Generalization
Total Generalization Error can be decomposed into:
$$\text{Total Error} = \text{Bias}^2 + \text{Variance} + \text{Irreducible Noise}$$

- **High Bias (Underfitting)**: Model makes strong, simplistic assumptions about data. Performs poorly on both training and test sets. Solution: Increase model complexity, add features, reduce regularization ($\lambda$).
- **High Variance (Overfitting)**: Model memorizes noise and specific idiosyncrasies in training set. High training accuracy, low test accuracy. Solution: Collect more training data, apply L1/L2 regularization, dropout, pruning, early stopping, or cross-validation.

## 3. Optimization and Gradient Descent
Gradient Descent iteratively updates model parameters $\theta$ in the direction of the negative gradient of the loss function $J(\theta)$:
$$\theta_{t+1} = \theta_t - \alpha \nabla J(\theta_t)$$
where $\alpha$ is the learning rate.

- **Batch Gradient Descent**: Uses the entire dataset to compute gradient at every step. Stable convergence, but slow for large datasets.
- **Stochastic Gradient Descent (SGD)**: Updates parameters using one sample at a time. Fast, can escape shallow local minima, but has noisy fluctuations.
- **Mini-Batch SGD**: Evaluates small batches (e.g., 32, 64, 128 samples). Combines computational efficiency with vectorization on GPUs.
- **Adaptive Optimizers**: Adam (Adaptive Moment Estimation) computes individual adaptive learning rates for different parameters from estimates of first and second moments of the gradients.

## 4. Evaluation Metrics for Classification
Given a Confusion Matrix with True Positives (TP), False Positives (FP), True Negatives (TN), and False Negatives (FN):

- **Accuracy**: $\frac{TP + TN}{TP + TN + FP + FN}$. Misleading for imbalanced datasets (e.g. cancer detection).
- **Precision**: $\frac{TP}{TP + FP}$. "Out of all predicted positives, how many were correct?" Crucial when false alarms are expensive (e.g., spam detection).
- **Recall (Sensitivity)**: $\frac{TP}{TP + FN}$. "Out of all actual positives, how many did we capture?" Crucial when missing a positive is catastrophic (e.g., medical diagnosis).
- **F1 Score**: Harmonic mean of Precision and Recall:
  $$F_1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$
- **ROC-AUC**: Receiver Operating Characteristic plots True Positive Rate against False Positive Rate across all thresholds. AUC of 1.0 represents a perfect classifier, 0.5 represents random guessing.
