import json
import sys
from bs4 import BeautifulSoup

def parse_services(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    services = []

    # Find the main container by ID
    main_container = soup.find('div', id='serviceListContent')
    if not main_container:
        print("Error: #serviceListContent not found.", file=sys.stderr)
        return services

    # Find all individual service boxes within the main container
    service_boxes = main_container.find_all('div', class_='serviceListContentBox')

    for box in service_boxes:
        title_anchor = box.select_one('.serviceListContentHeader h3 a')
        edit_link = box.select_one('.action a[href^="/mypage/services/"]')

        if title_anchor and edit_link:
            title = title_anchor.text.strip()
            service_url = title_anchor['href']
            # Assuming service_url is like /services/<service_id>
            service_id = service_url.split('/')[-1]
            edit_url = edit_link['href']

            services.append({
                'service_id': service_id,
                'title': title,
                'service_url': service_url,
                'edit_url': edit_url
            })
    return services

if __name__ == '__main__':
    html_input = sys.stdin.read()
    try:
        json_output = json.loads(html_input)
        html_content = json_output.get('html', '')
        parsed_services = parse_services(html_content)
        print(json.dumps(parsed_services, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))
