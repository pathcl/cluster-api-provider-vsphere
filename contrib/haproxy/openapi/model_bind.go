/*
Copyright 2020 The Kubernetes Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

/*
 * HAProxy Data Plane API
 *
 * API for editing and managing haproxy instances. Provides process information, configuration management, haproxy stats and logs.  # Authentication  <!-- ReDoc-Inject: <security-definitions> -->
 *
 * API version: 1.2
 * Contact: support@haproxy.com
 * Generated by: OpenAPI Generator (https://openapi-generator.tech)
 */

package openapi

// Bind HAProxy frontend bind configuration
type Bind struct {
	AcceptProxy    bool   `json:"accept_proxy,omitempty"`
	Address        string `json:"address,omitempty"`
	Alpn           string `json:"alpn,omitempty"`
	Name           string `json:"name"`
	Port           *int32 `json:"port,omitempty"`
	Process        string `json:"process,omitempty"`
	Ssl            bool   `json:"ssl,omitempty"`
	SslCafile      string `json:"ssl_cafile,omitempty"`
	SslCertificate string `json:"ssl_certificate,omitempty"`
	TcpUserTimeout *int32 `json:"tcp_user_timeout,omitempty"`
	Transparent    bool   `json:"transparent,omitempty"`
	V4v6           bool   `json:"v4v6,omitempty"`
	Verify         string `json:"verify,omitempty"`
}
