import requests
import os
import concurrent.futures

def fetch_ip_info(ip):
    """Fetches information for a single IP address."""
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        
        country = data.get('country', 'N/A')
        region = data.get('region', 'N/A')
        city = data.get('city', 'N/A')
        
        formatted_info = f"{ip}#{country},{region},{city}"
        print(formatted_info)
        return formatted_info
    except requests.exceptions.RequestException as e:
        print(f"Error fetching info for {ip}: {e}")
        return f"{ip}#Error"

def process_ips_multithreaded():
    """
    Reads IPs from ip.txt, fetches their info using multiple threads,
    and writes the results back to the file.
    """
    ip_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ip.txt')
    
    if not os.path.exists(ip_file_path):
        print(f"Error: {ip_file_path} not found.")
        return

    with open(ip_file_path, 'r') as f:
        ips = [line.strip() for line in f if line.strip()]

    results = []
    # Read max_workers from environment variable, default to 20
    max_workers = int(os.getenv('MAX_WORKERS', '20'))
    
    # Use ThreadPoolExecutor to fetch IP info in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # map submits tasks and returns an iterator of results in the same order
        future_to_ip = {executor.submit(fetch_ip_info, ip): ip for ip in ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            results.append(future.result())

    with open(ip_file_path, 'w') as f:
        for result in results:
            f.write(result + '\n')

if __name__ == "__main__":
    process_ips_multithreaded()