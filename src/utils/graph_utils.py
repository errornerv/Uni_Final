import matplotlib.pyplot as plt
import logging

def plot_graph(x, y, title, xlabel, ylabel, save_path=None):
    """
    Plot a graph and optionally save it to a file.
    """
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(x, y, marker='o')
        plt.title(title)
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.grid(True)

        if save_path:
            plt.savefig(save_path)
            logging.info(f"Graph saved to {save_path}")
        else:
            plt.show()
    except Exception as e:
        logging.error(f"Error while plotting graph: {e}")
        raise