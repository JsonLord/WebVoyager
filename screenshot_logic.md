# Screenshot Logic in WebVoyager

This document describes the screenshot logic used in WebVoyager, how it reacts to scrolling, and how it adapts to agent actions.

## Meta-Level Description

The screenshot logic in WebVoyager is a core component that enables the multimodal agent (e.g., GPT-4V) to perceive and interact with web pages. It employs a "Set-of-Mark" (SoM) prompting technique to bridge the gap between visual perception and action execution.

### 1. The "Set-of-Mark" Technique
Instead of sending a raw screenshot of the webpage, WebVoyager overlays numerical labels on top of interactive elements. This allows the agent to refer to elements by their assigned numbers (e.g., "Click [5]") rather than needing to describe the element's appearance or location in natural language.

### 2. The Iterative Workflow
The logic follows a strict "Mark -> Capture -> Clean" cycle in each iteration of the agent's loop:

1.  **Mark**: A JavaScript script is injected into the page to identify interactive elements (buttons, links, inputs, etc.) that are currently visible in the viewport. It draws dashed rectangles around these elements and adds a numerical label in the top-left corner.
2.  **Capture**: The Selenium WebDriver takes a screenshot of the current viewport, which now includes the overlaid labels.
3.  **Clean**: The added labels and rectangles are immediately removed from the DOM to restore the page to its original state, ensuring that the overlays do not interfere with subsequent agent actions (like clicking).

### 3. Reaction to Scrolling
Scrolling is handled dynamically. When the agent performs a `scroll` action (either on the window or a specific element), the page content shifts. In the next iteration, the marking script runs again. It uses `getBoundingClientRect()` and `elementFromPoint()` to determine which elements are *currently* visible and interactive within the *new* viewport. Consequently, labels are always accurately placed regardless of the scroll position.

### 4. Adaptation to Agent Actions
After every action (click, type, goback, etc.), the agent waits for the page to stabilize and then starts a new iteration. The re-marking process ensures that if an action causes the UI to change (e.g., opening a menu, navigating to a new page), the next screenshot will reflect those changes with a fresh set of labels corresponding to the new state.

---

## Code Snippets

### 1. Element Marking (JavaScript Injection)
The `markPage` function in `utils.py` is the heart of the labeling logic. It filters for interactive elements and ensures they are visible before drawing the labels.

```javascript
// Simplified excerpt from utils.py: get_web_element_rect
function markPage() {
    var items = Array.prototype.slice.call(
        document.querySelectorAll('*')
    ).map(function(element) {
        var vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
        var vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);

        // Ensure element is visible and at the front
        var rects = [...element.getClientRects()].filter(bb => {
            var center_x = bb.left + bb.width / 2;
            var center_y = bb.top + bb.height / 2;
            var elAtCenter = document.elementFromPoint(center_x, center_y);
            return elAtCenter === element || element.contains(elAtCenter);
        }).map(bb => {
            // ... calculate visible rect bounds ...
        });

        return {
            element: element,
            include: (element.tagName === "INPUT" || element.tagName === "BUTTON" || ...),
            area: ...,
            rects: rects,
            text: element.textContent.trim()
        };
    }).filter(item => item.include && (item.area >= 20));

    // Draw rectangles and labels
    items.forEach(function(item, index) {
        item.rects.forEach((bbox) => {
            let newElement = document.createElement("div");
            newElement.style.outline = "2px dashed #000000";
            newElement.style.position = "fixed";
            // ... set position based on bbox ...

            let label = document.createElement("span");
            label.textContent = index;
            // ... style label ...
            newElement.appendChild(label);
            document.body.appendChild(newElement);
        });
    });
    return [labels, items];
}
```

### 2. Capturing and Cleanup
In `run.py`, the agent calls `get_web_element_rect` to mark the page, saves the screenshot, and then removes the markers.

```python
# Excerpt from run.py: main loop
# 1. Mark the page
rects, web_eles, web_eles_text = get_web_element_rect(driver_task, fix_color=args.fix_box_color)

# 2. Capture the screenshot
img_path = os.path.join(task_dir, 'screenshot{}.png'.format(it))
driver_task.save_screenshot(img_path)

# ... (API call with screenshot) ...

# 3. Cleanup: Remove the rects from the website
if rects:
    for rect_ele in rects:
        driver_task.execute_script("arguments[0].remove()", rect_ele)
```

### 3. Handling Scrolling
Scrolling is treated as an action that triggers a new observation cycle.

```python
# Excerpt from run.py: exec_action_scroll
def exec_action_scroll(info, web_eles, driver_task, args, obs_info):
    if scroll_ele_number == "WINDOW":
        if scroll_content == 'down':
            driver_task.execute_script(f"window.scrollBy(0, {args.window_height*2//3});")
        else:
            driver_task.execute_script(f"window.scrollBy(0, {-args.window_height*2//3});")
    # ... after scrolling, the loop continues, re-marking the page in the next iteration
```
