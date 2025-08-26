"""
cato.py

A simple wrapper for Cato API queries.
"""

import certifi
import gzip
import json
import ssl
import urllib.parse
import urllib.request


class API:
	"""
	Simple class to make API queries. Includes:

	* Automatic response compression.
	* Error handling.
	"""


	def __init__(self, key, url='https://api.catonetworks.com/api/v1/graphql2'):
		"""
		Instantiate object with API key.
		"""
		self._key = key
		self._url = url


	def send(self, operation, variables, query):
		"""
		Send an API request and return the response as a Python object.

		Returns a tuple consisting of a boolean success flag, and a Python object
		converted from the JSON response.
		"""
		body = json.dumps({
			"operationName": operation,
			"query":query,
			"variables":variables
		}).encode("ascii")
		headers = {
			"Content-Type": "application/json",
			"Accept-Encoding": "gzip, deflate, br",
			"X-api-key": self._key
		}
		try:
			request = urllib.request.Request(
				url=self._url,
				data=body,
				headers=headers
			)
			# Create secure SSL context with minimum TLS 1.2
			context = ssl.create_default_context(cafile=certifi.where())
			context.minimum_version = ssl.TLSVersion.TLSv1_2
			
			response = urllib.request.urlopen(
				request, 
				context=context,
				timeout=10
			)
			response_data = gzip.decompress(response.read())
			response_obj = json.loads(response_data.decode('utf-8','replace'))
		except urllib.error.HTTPError as e:
			# Log HTTP errors without exposing sensitive details
			return False, {"error": f"HTTP error {e.code}"}
		except urllib.error.URLError:
			# Network connectivity issues
			return False, {"error": "Network connection failed"}
		except json.JSONDecodeError:
			# Invalid JSON response
			return False, {"error": "Invalid response format"}
		except Exception:
			# Generic error without exposing details
			return False, {"error": "API request failed"}
		if "errors" in response_obj:
			return False, response_obj
		else:
			return True, response_obj

