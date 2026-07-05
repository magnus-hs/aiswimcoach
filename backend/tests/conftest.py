"""
Test configuration for backend tests.

Ensures that modules imported as 'backend.X' and 'X' resolve to the same
module object, preventing class identity mismatches when patching.
"""
import sys
import os

# Add backend directory to sys.path so bare imports resolve correctly
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import key modules using bare names first, so they're registered in sys.modules
# Then alias them under 'backend.' prefix to ensure identity consistency
import auth  # noqa: E402
import middleware  # noqa: E402
import handler  # noqa: E402
import models  # noqa: E402
import multipart_parser  # noqa: E402
import s3_store  # noqa: E402
import fit_parser  # noqa: E402
import bedrock_client  # noqa: E402
import profile_manager  # noqa: E402
import chat_history_store  # noqa: E402

# Register the same module objects under both names
sys.modules.setdefault('backend.auth', auth)
sys.modules.setdefault('backend.middleware', middleware)
sys.modules.setdefault('backend.handler', handler)
sys.modules.setdefault('backend.models', models)
sys.modules.setdefault('backend.multipart_parser', multipart_parser)
sys.modules.setdefault('backend.s3_store', s3_store)
sys.modules.setdefault('backend.fit_parser', fit_parser)
sys.modules.setdefault('backend.bedrock_client', bedrock_client)
sys.modules.setdefault('backend.profile_manager', profile_manager)
sys.modules.setdefault('backend.chat_history_store', chat_history_store)
