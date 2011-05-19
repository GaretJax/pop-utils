# TODO: Move the File["/etc/apt/sources.list"] and Exec["update"] resources to
#       the pre stage once the distributed puppet versions supports it.

file { "/etc/apt/sources.list":
	content => "deb http://archive.ubuntu.com/ubuntu/ lucid main universe
deb-src http://archive.ubuntu.com/ubuntu/ lucid main universe
deb http://archive.ubuntu.com/ubuntu/ lucid-updates main universe
deb-src http://archive.ubuntu.com/ubuntu/ lucid-updates main universe
deb http://security.ubuntu.com/ubuntu lucid-security main universe
deb-src http://security.ubuntu.com/ubuntu lucid-security main universe",
}

exec { "update":
	command => "/usr/bin/apt-get -y update",
	require => File["/etc/apt/sources.list"],
}
exec { "upgrade":
	command => "/usr/bin/apt-get -y upgrade",
	require => Exec["update"],
}
exec { "dist-upgrade":
	command => "/usr/bin/apt-get -y dist-upgrade",
	require => Exec["upgrade"],
}


# AWS and Image bundling tools
package { "cloud-utils":
	ensure => installed,
	require => Exec["dist-upgrade"],
}

# POP-C++ dependencies
package { "g++":
	ensure => installed,
	require => Exec["dist-upgrade"],
}
package { "zlib1g-dev":
	ensure => installed,
	require => Exec["dist-upgrade"],
}

# POP-Java dependencies
package { "openjdk-6-jre-headless":
	ensure => installed,
	require => Exec["dist-upgrade"],
}

# Web server
package { "lighttpd":
	ensure => installed,
	require => Exec["dist-upgrade"],
}
service { "lighttpd":
	ensure => running,
	require => Package["lighttpd"],
}

# Other tools
package { "python-setuptools":
	ensure => installed,
	require => Exec["dist-upgrade"],
}
package { "python-dev":
	ensure => installed,
	require => Exec["dist-upgrade"],
}
package { "python-lxml":
	ensure => installed,
	require => Exec["dist-upgrade"],
}

exec { "easy_install fabric":
	path => ['/usr/local/bin', '/usr/bin', '/bin'],
	require => [Package["python-setuptools"], Package["python-dev"]],
}


