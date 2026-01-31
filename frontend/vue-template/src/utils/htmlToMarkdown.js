/**
 * Simple HTML to Markdown converter
 * Supports: Headers, Lists, Bold, Italic, Paragraphs
 */
export function htmlToMarkdown(html) {
    if (!html) return ''

    // Create a temporary DOM element to traverse
    const tempDiv = document.createElement('div')
    tempDiv.innerHTML = html

    let markdown = ''

    function traverse(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            return node.textContent
        }

        if (node.nodeType !== Node.ELEMENT_NODE) {
            return ''
        }

        let result = ''
        const children = Array.from(node.childNodes)

        switch (node.tagName.toLowerCase()) {
            case 'h1':
                result += '# ' + children.map(traverse).join('') + '\n\n'
                break
            case 'h2':
                result += '## ' + children.map(traverse).join('') + '\n\n'
                break
            case 'h3':
                result += '### ' + children.map(traverse).join('') + '\n\n'
                break
            case 'p':
            case 'div': // div often behaves like p in contenteditable
                const content = children.map(traverse).join('')
                if (content.trim()) {
                    result += content + '\n\n'
                }
                break
            case 'strong':
            case 'b':
                result += '**' + children.map(traverse).join('') + '**'
                break
            case 'em':
            case 'i':
                result += '*' + children.map(traverse).join('') + '*'
                break
            case 'ul':
                result += children.map(traverse).join('') + '\n'
                break
            case 'ol':
                // For simple impl, treating ol as ul or manual numbering could apply, 
                // but let's try to map li children
                children.forEach((child, index) => {
                    if (child.tagName?.toLowerCase() === 'li') {
                        result += `1. ${traverse(child)}\n` // Simple Ordered list
                    } else {
                        result += traverse(child)
                    }
                })
                result += '\n'
                break
            case 'li':
                // Check parent to decide bullet
                const parentTag = node.parentElement?.tagName?.toLowerCase()
                if (parentTag === 'ol') {
                    return children.map(traverse).join('') // Handled in parent loop ideally, but for simple recursion:
                }
                result += '- ' + children.map(traverse).join('') + '\n'
                break
            case 'br':
                result += '\n'
                break
            default:
                result += children.map(traverse).join('')
                break
        }

        return result
    }

    markdown = traverse(tempDiv)

    // Clean up excessive newlines
    return markdown.replace(/\n{3,}/g, '\n\n').trim()
}
