/**
 * MinHeap-based Priority Queue for Space-Time A* pathfinding.
 * Elements are dequeued in order of ascending priority (f-value).
 */
class PriorityQueue {
    constructor() {
        this.heap = [];
    }

    get size() {
        return this.heap.length;
    }

    isEmpty() {
        return this.heap.length === 0;
    }

    push(item, priority) {
        this.heap.push({ item, priority });
        this._bubbleUp(this.heap.length - 1);
    }

    pop() {
        if (this.heap.length === 0) return null;
        const top = this.heap[0];
        const last = this.heap.pop();
        if (this.heap.length > 0) {
            this.heap[0] = last;
            this._sinkDown(0);
        }
        return top.item;
    }

    peek() {
        return this.heap.length > 0 ? this.heap[0].item : null;
    }

    _bubbleUp(i) {
        while (i > 0) {
            const parent = Math.floor((i - 1) / 2);
            if (this.heap[parent].priority <= this.heap[i].priority) break;
            [this.heap[parent], this.heap[i]] = [this.heap[i], this.heap[parent]];
            i = parent;
        }
    }

    _sinkDown(i) {
        const n = this.heap.length;
        while (true) {
            let smallest = i;
            const left = 2 * i + 1;
            const right = 2 * i + 2;
            if (left < n && this.heap[left].priority < this.heap[smallest].priority) {
                smallest = left;
            }
            if (right < n && this.heap[right].priority < this.heap[smallest].priority) {
                smallest = right;
            }
            if (smallest === i) break;
            [this.heap[smallest], this.heap[i]] = [this.heap[i], this.heap[smallest]];
            i = smallest;
        }
    }
}
