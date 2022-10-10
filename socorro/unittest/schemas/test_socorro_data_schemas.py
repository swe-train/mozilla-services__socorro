# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from click.testing import CliRunner
import jsonschema
import pytest

from socorro.lib.libsocorrodataschema import (
    get_schema,
    FlattenKeys,
    split_path,
    transform_schema,
)
from socorro.schemas import get_file_content
from socorro.schemas.validate_processed_crash import (
    validate_and_test as processed_validate,
)
from socorro.schemas.validate_raw_crash import validate_and_test as raw_validate


def test_validate_socorro_data_schema():
    """Assert that socorro-data-1-0-0.schema.yaml is valid jsonschema"""
    schema = get_file_content("socorro-data-1-0-0.schema.yaml")
    jsonschema.Draft7Validator.check_schema(schema)


def test_validate_raw_crash_cli_runs():
    """Test whether the script loads and spits out help."""
    runner = CliRunner()
    result = runner.invoke(raw_validate, ["--help"])
    assert result.exit_code == 0


def test_validate_raw_crash_schema():
    # We use the schema reducer to traverse the schema and validate the socorro metadata
    # values
    schema = get_file_content("socorro-data-1-0-0.schema.yaml")
    raw_crash_schema = get_file_content("raw_crash.schema.yaml")

    jsonschema.validate(instance=raw_crash_schema, schema=schema)


PUBLIC_RAW_CRASH_FIELDS = {
    "AbortMessage",
    "Accessibility",
    "AccessibilityClient",
    "AccessibilityInProcClient",
    "AdapterDeviceID",
    "AdapterDriverVersion",
    "AdapterSubsysID",
    "AdapterVendorID",
    "Add-ons",
    "Android_Board",
    "Android_Brand",
    "Android_CPU_ABI",
    "Android_CPU_ABI2",
    "Android_Device",
    "Android_Display",
    "Android_Fingerprint",
    "Android_Hardware",
    "Android_Manufacturer",
    "Android_Model",
    "Android_Version",
    "AppInitDLLs",
    "ApplicationBuildID",
    "AsyncShutdownTimeout",
    "AvailablePageFile",
    "AvailablePhysicalMemory",
    "AvailableVirtualMemory",
    "BuildID",
    "CPUMicrocodeVersion",
    "CoMarshalInterfaceFailure",
    "CoUnmarshalInterfaceResult",
    "ContentSandboxCapabilities",
    "ContentSandboxCapable",
    "ContentSandboxEnabled",
    "ContentSandboxLevel",
    "CrashTime",
    "DOMFissionEnabled",
    "DOMIPCEnabled",
    "DistributionID",
    "EMCheckCompatibility",
    "GMPPlugin",
    "GraphicsCriticalError",
    "GraphicsStartupTest",
    "HasDeviceTouchScreen",
    "IPCFatalErrorMsg",
    "IPCFatalErrorProtocol",
    "IPCMessageName",
    "IPCMessageSize",
    "IPCShutdownState",
    "IPCSystemError",
    "InstallTime",
    "IsGarbageCollecting",
    "MacAvailableMemorySysctl",
    "MacMemoryPressure",
    "MacMemoryPressureCriticalTime",
    "MacMemoryPressureNormalTime",
    "MacMemoryPressureSysctl",
    "MacMemoryPressureWarningTime",
    "Notes",
    "OOMAllocationSize",
    "PluginFilename",
    "PluginName",
    "PluginVersion",
    "ProcessType",
    "ProductID",
    "ProductName",
    "ReleaseChannel",
    "SafeMode",
    "SecondsSinceLastCrash",
    "ShutdownProgress",
    "StartupCrash",
    "StartupTime",
    "SubmittedFrom",
    "SubmittedFromInfobar",
    "SystemMemoryUsePercentage",
    "TelemetryEnvironment",
    "Throttleable",
    "TotalPageFile",
    "TotalPhysicalMemory",
    "TotalVirtualMemory",
    "UptimeTS",
    "UtilityProcessSandboxingKind",
    "Vendor",
    "Version",
    "WindowsErrorReporting",
    "Winsock_LSP",
    "XPCOMSpinEventLoopStack",
    "ipc_channel_error",
    "submitted_timestamp",
    "useragent_locale",
    "uuid",
    "version",
}


class InvalidRawCrashField(Exception):
    pass


def test_raw_crash_permissions():
    public_fields = []

    def verify_permissions(path, schema_item):
        if not path:
            return schema_item

        permissions = schema_item.get("permissions", [])

        # All items should have permissions explicitly set
        if not permissions:
            raise InvalidRawCrashField(
                f'{path} does not have permissions set; set to either ["public"] or '
                + "some list of permissions"
            )

        # Permissions should be ["public"] OR some list of permissions
        if "public" in permissions and permissions != ["public"]:
            raise InvalidRawCrashField(
                f'{path} permissions should be either ["public"] or some list of '
                + "permissions"
            )

        if "array" not in schema_item["type"] and permissions == ["public"]:
            # Add the path to the list of public fields without the initial "."
            public_fields.append(path[1:])

        return schema_item

    raw_crash_schema = get_schema("raw_crash.schema.yaml")

    # This will raise an exception if there are invalid permissions
    transform_schema(schema=raw_crash_schema, transform_function=verify_permissions)

    # Verify that the list of public fields is what we expect. This helps to alleviate
    # inadvertently making a field public that you didn't intend to make public.
    assert set(public_fields) == PUBLIC_RAW_CRASH_FIELDS


def test_validate_processed_crash_cli_runs():
    """Test whether the script loads and spits out help."""
    runner = CliRunner()
    result = runner.invoke(processed_validate, ["--help"])
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "path, expected",
    [
        ("", []),
        (".java_exception", ["java_exception"]),
        (
            ".java_exception.exception.values.[].stacktrace.frames.[].filename",
            [
                "java_exception",
                "exception",
                "values",
                "[]",
                "stacktrace",
                "frames",
                "[]",
                "filename",
            ],
        ),
        (
            ".json_dump.crashing_thread.frames.[].registers.(re:^.+$)",
            ["json_dump", "crashing_thread", "frames", "[]", "registers", "(re:^.+$)"],
        ),
    ],
)
def test_split_parts(path, expected):
    assert list(split_path(path)) == expected


def test_validate_processed_crash_schema():
    # We use the schema reducer to traverse the schema and validate the socorro metadata
    # values
    schema = get_file_content("socorro-data-1-0-0.schema.yaml")
    processed_crash_schema = get_file_content("processed_crash.schema.yaml")

    jsonschema.validate(instance=processed_crash_schema, schema=schema)


PUBLIC_PROCESSED_CRASH_FIELDS = {
    "abort_message",
    "accessibility",
    "accessibility_client",
    "accessibility_in_proc_client",
    "adapter_device_id",
    "adapter_driver_version",
    "adapter_subsys_id",
    "adapter_vendor_id",
    "additional_minidumps.[]",
    "addons.[]",
    "addons_checked",
    "address",
    "android_board",
    "android_brand",
    "android_cpu_abi",
    "android_cpu_abi2",
    "android_device",
    "android_display",
    "android_fingerprint",
    "android_hardware",
    "android_manufacturer",
    "android_model",
    "android_version",
    "app_init_dlls",
    "app_notes",
    "application_build_id",
    "async_shutdown_timeout",
    "available_page_file",
    "available_physical_memory",
    "available_virtual_memory",
    "build",
    "client_crash_date",
    "co_marshal_interface_failure",
    "co_unmarshal_interface_result",
    "completed_datetime",
    "content_sandbox_capabilities",
    "content_sandbox_capable",
    "content_sandbox_enabled",
    "content_sandbox_level",
    "cpu_arch",
    "cpu_count",
    "cpu_info",
    "cpu_microcode_version",
    "crash_id",
    "crash_report_keys.[]",
    "crash_time",
    "crashing_thread",
    "crashing_thread_name",
    "date_processed",
    "distribution_id",
    "dom_fission_enabled",
    "dom_ipc_enabled",
    "em_check_compatibility",
    "gmp_plugin",
    "graphics_critical_error",
    "graphics_startup_test",
    "has_device_touch_screen",
    "install_age",
    "install_time",
    "ipc_channel_error",
    "ipc_fatal_error_msg",
    "ipc_fatal_error_protocol",
    "ipc_message_name",
    "ipc_message_size",
    "ipc_shutdown_state",
    "ipc_system_error",
    "is_garbage_collecting",
    "java_exception",
    "java_exception.exception",
    "java_exception.exception.values.[]",
    "java_exception.exception.values.[].stacktrace",
    "java_exception.exception.values.[].stacktrace.frames.[]",
    "java_exception.exception.values.[].stacktrace.frames.[].filename",
    "java_exception.exception.values.[].stacktrace.frames.[].function",
    "java_exception.exception.values.[].stacktrace.frames.[].in_app",
    "java_exception.exception.values.[].stacktrace.frames.[].lineno",
    "java_exception.exception.values.[].stacktrace.frames.[].module",
    "java_exception.exception.values.[].stacktrace.module",
    "java_exception.exception.values.[].stacktrace.type",
    "java_stack_trace",
    "json_dump",
    "json_dump.crash_info",
    "json_dump.crash_info.address",
    "json_dump.crash_info.assertion",
    "json_dump.crash_info.crashing_thread",
    "json_dump.crash_info.type",
    "json_dump.crashing_thread",
    "json_dump.crashing_thread.frame_count",
    "json_dump.crashing_thread.frames.[]",
    "json_dump.crashing_thread.frames.[].file",
    "json_dump.crashing_thread.frames.[].frame",
    "json_dump.crashing_thread.frames.[].function",
    "json_dump.crashing_thread.frames.[].function_offset",
    "json_dump.crashing_thread.frames.[].inlines.[]",
    "json_dump.crashing_thread.frames.[].inlines.[].file",
    "json_dump.crashing_thread.frames.[].inlines.[].function",
    "json_dump.crashing_thread.frames.[].inlines.[].line",
    "json_dump.crashing_thread.frames.[].line",
    "json_dump.crashing_thread.frames.[].missing_symbols",
    "json_dump.crashing_thread.frames.[].module",
    "json_dump.crashing_thread.frames.[].module_offset",
    "json_dump.crashing_thread.frames.[].offset",
    "json_dump.crashing_thread.frames.[].trust",
    "json_dump.crashing_thread.frames.[].unloaded_modules.[]",
    "json_dump.crashing_thread.frames.[].unloaded_modules.[].module",
    "json_dump.crashing_thread.frames.[].unloaded_modules.[].offsets.[]",
    "json_dump.crashing_thread.last_error_value",
    "json_dump.crashing_thread.thread_name",
    "json_dump.crashing_thread.threads_index",
    "json_dump.lsb_release",
    "json_dump.lsb_release.codename",
    "json_dump.lsb_release.description",
    "json_dump.lsb_release.id",
    "json_dump.lsb_release.release",
    "json_dump.mac_crash_info",
    "json_dump.mac_crash_info.num_records",
    "json_dump.mac_crash_info.records.[]",
    "json_dump.mac_crash_info.records.[].abort_cause",
    "json_dump.mac_crash_info.records.[].backtrace",
    "json_dump.mac_crash_info.records.[].dialog_mode",
    "json_dump.mac_crash_info.records.[].message",
    "json_dump.mac_crash_info.records.[].message2",
    "json_dump.mac_crash_info.records.[].module",
    "json_dump.mac_crash_info.records.[].signature_string",
    "json_dump.mac_crash_info.records.[].thread",
    "json_dump.main_module",
    "json_dump.modules.[]",
    "json_dump.modules.[].base_addr",
    "json_dump.modules.[].cert_subject",
    "json_dump.modules.[].code_id",
    "json_dump.modules.[].corrupt_symbols",
    "json_dump.modules.[].debug_file",
    "json_dump.modules.[].debug_id",
    "json_dump.modules.[].end_addr",
    "json_dump.modules.[].filename",
    "json_dump.modules.[].loaded_symbols",
    "json_dump.modules.[].missing_symbols",
    "json_dump.modules.[].symbol_url",
    "json_dump.modules.[].version",
    "json_dump.modules_contains_cert_info",
    "json_dump.pid",
    "json_dump.status",
    "json_dump.system_info",
    "json_dump.system_info.cpu_arch",
    "json_dump.system_info.cpu_count",
    "json_dump.system_info.cpu_info",
    "json_dump.system_info.cpu_microcode_version",
    "json_dump.system_info.os",
    "json_dump.system_info.os_ver",
    "json_dump.thread_count",
    "json_dump.threads.[]",
    "json_dump.threads.[].frame_count",
    "json_dump.threads.[].frames.[]",
    "json_dump.threads.[].frames.[].file",
    "json_dump.threads.[].frames.[].frame",
    "json_dump.threads.[].frames.[].function",
    "json_dump.threads.[].frames.[].function_offset",
    "json_dump.threads.[].frames.[].inlines.[]",
    "json_dump.threads.[].frames.[].inlines.[].file",
    "json_dump.threads.[].frames.[].inlines.[].function",
    "json_dump.threads.[].frames.[].inlines.[].line",
    "json_dump.threads.[].frames.[].line",
    "json_dump.threads.[].frames.[].missing_symbols",
    "json_dump.threads.[].frames.[].module",
    "json_dump.threads.[].frames.[].module_offset",
    "json_dump.threads.[].frames.[].offset",
    "json_dump.threads.[].frames.[].trust",
    "json_dump.threads.[].frames.[].unloaded_modules.[]",
    "json_dump.threads.[].frames.[].unloaded_modules.[].module",
    "json_dump.threads.[].frames.[].unloaded_modules.[].offsets.[]",
    "json_dump.threads.[].last_error_value",
    "json_dump.threads.[].thread_name",
    "json_dump.unloaded_modules.[]",
    "json_dump.unloaded_modules.[].base_addr",
    "json_dump.unloaded_modules.[].cert_subject",
    "json_dump.unloaded_modules.[].code_id",
    "json_dump.unloaded_modules.[].end_addr",
    "json_dump.unloaded_modules.[].filename",
    "last_crash",
    "mac_available_memory_sysctl",
    "mac_crash_info",
    "mac_memory_pressure",
    "mac_memory_pressure_critical_time",
    "mac_memory_pressure_normal_time",
    "mac_memory_pressure_sysctl",
    "mac_memory_pressure_warning_time",
    "major_version",
    "mdsw_status_string",
    "memory_measures",
    "memory_measures.explicit",
    "memory_measures.gfx_textures",
    "memory_measures.ghost_windows",
    "memory_measures.heap_allocated",
    "memory_measures.heap_overhead",
    "memory_measures.heap_unclassified",
    "memory_measures.host_object_urls",
    "memory_measures.images",
    "memory_measures.js_main_runtime",
    "memory_measures.private",
    "memory_measures.resident",
    "memory_measures.resident_unique",
    "memory_measures.system_heap_allocated",
    "memory_measures.top_none_detached",
    "memory_measures.vsize",
    "memory_measures.vsize_max_contiguous",
    "minidump_sha256_hash",
    "modules_in_stack",
    "moz_crash_reason",
    "oom_allocation_size",
    "os_name",
    "os_pretty_version",
    "os_version",
    "plugin_filename",
    "plugin_name",
    "plugin_version",
    "process_type",
    "processor_notes",
    "product",
    "productid",
    "proto_signature",
    "reason",
    "release_channel",
    "safe_mode",
    "shutdown_progress",
    "signature",
    "stackwalk_version",
    "started_datetime",
    "startup_crash",
    "startup_time",
    "submitted_from",
    "submitted_timestamp",
    "success",
    "system_memory_use_percentage",
    "throttleable",
    "topmost_filenames",
    "total_page_file",
    "total_physical_memory",
    "total_virtual_memory",
    "upload_file_minidump_browser",
    "upload_file_minidump_browser.json_dump",
    "upload_file_minidump_browser.json_dump.crash_info",
    "upload_file_minidump_browser.json_dump.crash_info.address",
    "upload_file_minidump_browser.json_dump.crash_info.assertion",
    "upload_file_minidump_browser.json_dump.crash_info.crashing_thread",
    "upload_file_minidump_browser.json_dump.crash_info.type",
    "upload_file_minidump_browser.json_dump.crashing_thread",
    "upload_file_minidump_browser.json_dump.crashing_thread.frame_count",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[]",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].file",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].frame",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].function",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].function_offset",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].inlines.[]",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].inlines.[].file",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].inlines.[].function",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].inlines.[].line",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].line",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].missing_symbols",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].module",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].module_offset",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].offset",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].trust",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].unloaded_modules.[]",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].unloaded_modules.[].module",
    "upload_file_minidump_browser.json_dump.crashing_thread.frames.[].unloaded_modules.[].offsets.[]",
    "upload_file_minidump_browser.json_dump.crashing_thread.last_error_value",
    "upload_file_minidump_browser.json_dump.crashing_thread.thread_name",
    "upload_file_minidump_browser.json_dump.crashing_thread.threads_index",
    "upload_file_minidump_browser.json_dump.lsb_release",
    "upload_file_minidump_browser.json_dump.lsb_release.codename",
    "upload_file_minidump_browser.json_dump.lsb_release.description",
    "upload_file_minidump_browser.json_dump.lsb_release.id",
    "upload_file_minidump_browser.json_dump.lsb_release.release",
    "upload_file_minidump_browser.json_dump.mac_crash_info",
    "upload_file_minidump_browser.json_dump.mac_crash_info.num_records",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[]",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].abort_cause",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].backtrace",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].dialog_mode",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].message",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].message2",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].module",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].signature_string",
    "upload_file_minidump_browser.json_dump.mac_crash_info.records.[].thread",
    "upload_file_minidump_browser.json_dump.main_module",
    "upload_file_minidump_browser.json_dump.modules.[]",
    "upload_file_minidump_browser.json_dump.modules.[].base_addr",
    "upload_file_minidump_browser.json_dump.modules.[].cert_subject",
    "upload_file_minidump_browser.json_dump.modules.[].code_id",
    "upload_file_minidump_browser.json_dump.modules.[].corrupt_symbols",
    "upload_file_minidump_browser.json_dump.modules.[].debug_file",
    "upload_file_minidump_browser.json_dump.modules.[].debug_id",
    "upload_file_minidump_browser.json_dump.modules.[].end_addr",
    "upload_file_minidump_browser.json_dump.modules.[].filename",
    "upload_file_minidump_browser.json_dump.modules.[].loaded_symbols",
    "upload_file_minidump_browser.json_dump.modules.[].missing_symbols",
    "upload_file_minidump_browser.json_dump.modules.[].symbol_url",
    "upload_file_minidump_browser.json_dump.modules.[].version",
    "upload_file_minidump_browser.json_dump.modules_contains_cert_info",
    "upload_file_minidump_browser.json_dump.pid",
    "upload_file_minidump_browser.json_dump.status",
    "upload_file_minidump_browser.json_dump.system_info",
    "upload_file_minidump_browser.json_dump.system_info.cpu_arch",
    "upload_file_minidump_browser.json_dump.system_info.cpu_count",
    "upload_file_minidump_browser.json_dump.system_info.cpu_info",
    "upload_file_minidump_browser.json_dump.system_info.cpu_microcode_version",
    "upload_file_minidump_browser.json_dump.system_info.os",
    "upload_file_minidump_browser.json_dump.system_info.os_ver",
    "upload_file_minidump_browser.json_dump.thread_count",
    "upload_file_minidump_browser.json_dump.threads.[]",
    "upload_file_minidump_browser.json_dump.threads.[].frame_count",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[]",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].file",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].frame",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].function",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].function_offset",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].inlines.[]",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].inlines.[].file",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].inlines.[].function",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].inlines.[].line",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].line",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].missing_symbols",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].module",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].module_offset",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].offset",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].trust",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].unloaded_modules.[]",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].unloaded_modules.[].module",
    "upload_file_minidump_browser.json_dump.threads.[].frames.[].unloaded_modules.[].offsets.[]",
    "upload_file_minidump_browser.json_dump.threads.[].last_error_value",
    "upload_file_minidump_browser.json_dump.threads.[].thread_name",
    "upload_file_minidump_browser.json_dump.unloaded_modules.[]",
    "upload_file_minidump_browser.json_dump.unloaded_modules.[].base_addr",
    "upload_file_minidump_browser.json_dump.unloaded_modules.[].cert_subject",
    "upload_file_minidump_browser.json_dump.unloaded_modules.[].code_id",
    "upload_file_minidump_browser.json_dump.unloaded_modules.[].end_addr",
    "upload_file_minidump_browser.json_dump.unloaded_modules.[].filename",
    "upload_file_minidump_browser.mdsw_status_string",
    "upload_file_minidump_browser.stackwalk_version",
    "upload_file_minidump_browser.success",
    "uptime",
    "uptime_ts",
    "useragent_locale",
    "utility_process_sandboxing_kind",
    "uuid",
    "vendor",
    "version",
    "windows_error_reporting",
    "xpcom_spin_event_loop_stack",
}


class InvalidProcessedCrashField(Exception):
    pass


def test_processed_crash_permissions():
    public_fields = []

    def verify_permissions(path, schema_item):
        if not path:
            return schema_item

        permissions = schema_item.get("permissions", [])

        # All items should have permissions explicitly set
        if not permissions:
            raise InvalidProcessedCrashField(
                f'{path} does not have permissions set; set to either ["public"] or '
                + "some list of permissions"
            )

        # Permissions should be ["public"] OR some list of permissions
        if "public" in permissions and permissions != ["public"]:
            raise InvalidProcessedCrashField(
                f'{path} permissions should be either ["public"] or some list of '
                + "permissions"
            )

        if "array" not in schema_item["type"] and permissions == ["public"]:
            # Add the path to the list of public fields without the initial "."
            public_fields.append(path[1:])

        return schema_item

    processed_crash_schema = get_schema("processed_crash.schema.yaml")

    # This will raise an exception if there are invalid permissions
    transform_schema(
        schema=processed_crash_schema, transform_function=verify_permissions
    )

    # Verify that the list of public fields is what we expect. This helps to alleviate
    # inadvertently making a field public that you didn't intend to make public.
    assert set(public_fields) == PUBLIC_PROCESSED_CRASH_FIELDS


def test_processed_crash_source_annotations():
    # Get the list of raw crash keys
    raw_crash_schema = get_schema("raw_crash.schema.yaml")
    flattener = FlattenKeys()
    transform_schema(schema=raw_crash_schema, transform_function=flattener.flatten)
    raw_crash_keys = flattener.keys

    def verify_source_annotations(path, schema_item):
        if not path:
            return schema_item

        permissions = schema_item.get("permissions", [])

        source = schema_item.get("source_annotation")
        if source:
            # If the source_annotation is not a valid field in the raw crash schema,
            # then it's invalid
            if source not in raw_crash_keys:
                raise InvalidProcessedCrashField(f"{path} is not in raw the raw crash")

            # If the processed crash field permissions is ["public"] and it's not an
            # object and it has a source_annotation, then the raw crash field must also
            # be public
            if (
                permissions == ["public"]
                and schema_item["type"] != "object"
                and source not in PUBLIC_RAW_CRASH_FIELDS
            ):
                raise InvalidProcessedCrashField(
                    f"{path} is public and has source annotation {source} that is "
                    + "not public"
                )

        return schema_item

    # This will raise an exception if there are invalid permissions
    processed_crash_schema = get_schema("processed_crash.schema.yaml")

    transform_schema(
        schema=processed_crash_schema, transform_function=verify_source_annotations
    )
